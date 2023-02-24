
from typing import Optional
import os, subprocess, re, shutil

from mhubio.Config import Config, Instance, InstanceData, DataType, FileType, CT, SEG
from mhubio.modules.runner.ModelRunner import ModelRunner


class NNUnetRunner(ModelRunner):

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._nnunet_model: Optional[str] = None
        self._nnunet_model_available_options = ["2d", "3d_lowres", "3d_fullres", "3d_cascade_fullres"]
        self._input_data_type: DataType = DataType(FileType.NIFTI, CT)
        self._nnunet_task_name: Optional[str] = None

    @property
    def nnunet_task(self) -> str:
        nnunet_task_name_config_key = 'task'
        if self._nnunet_task_name is not None:
            return self._nnunet_task_name
        elif nnunet_task_name_config_key in self.c:
            return self.c[nnunet_task_name_config_key]
        else:          
            raise ValueError("No task set for nnunet runner.")

    @nnunet_task.setter
    def nnunet_task(self, nnunet_task_name: str) -> None:
        # regular expression for nnunet task names
        nnunet_task_name_regex = r"Task[0-9]{3}_[a-zA-Z0-9_]+"
        if not re.match(nnunet_task_name_regex, nnunet_task_name):
            raise ValueError("Invalid nnunet task name.")
        
        # set task name (overrides any coniguration from the confif.yml file)
        self._nnunet_task_name = nnunet_task_name

    @property
    def nnunet_model(self) -> str:
        nnunet_model_config_key = 'model'
        if self._nnunet_model is not None and self._nnunet_model in self._nnunet_model_available_options:
            return self._nnunet_model
        elif nnunet_model_config_key in self.c and self.c[nnunet_model_config_key] in self._nnunet_model_available_options:
            return self.c[nnunet_model_config_key]
        else:
            raise ValueError("No model set for nnunet runner.")

    @nnunet_model.setter
    def nnunet_model(self, nnunet_model: str) -> None:
        assert nnunet_model in self._nnunet_model_available_options
        self._nnunet_model = nnunet_model

    @property
    def input_type(self) -> DataType:
        return self._input_data_type
    
    @input_type.setter
    def input_type(self, type: DataType) -> None:
        self._input_data_type = type


    def runModel(self, instance: Instance) -> None:
        
        # get the nnunet model to run
        print("Running nnUNet_predict.")
        print(f" > task: {self.nnunet_task}")
        print(f" > model: {self.nnunet_model}")

        # download weights if not found
        # NOTE: only for testing / debugging. For productiio always provide the weights in the Docker container.
        if not os.path.isdir(os.path.join(os.environ["WEIGHTS_FOLDER"], '')):
            print("Downloading nnUNet model weights...")
            bash_command = ["nnUNet_download_pretrained_model", self.nnunet_task]
            _ = subprocess.run(bash_command, stdout=subprocess.PIPE)

        # get input data
        inp_data = instance.getData(self._input_data_type)

        # bring input data in nnunet specific format
        # NOTE: only for nifti data as we hardcode the nnunet-formatted-filename (and extension) for now.
        assert inp_data.type.ftype == FileType.NIFTI
        assert inp_data.abspath.endswith('.nii.gz')
        inp_dir = self.config.data.requestTempDir(label="nnunet-model-inp")
        inp_file = f'VOLUME_001_0000.nii.gz'
        shutil.copyfile(inp_data.abspath, os.path.join(inp_dir, inp_file))

        # define output folder (temp dir) and also override environment variable for nnunet
        out_dir = self.config.data.requestTempDir(label="nnunet-model-out")
        os.environ['RESULTS_FOLDER'] = out_dir

        # symlink nnunet input folder to the input data with python
        # create symlink in python
        # NOTE: this is a workaround for the nnunet bash script that expects the input data to be in a specific folder
        #       structure. This is not the case for the mhub data structure. So we create a symlink to the input data
        #       in the nnunet input folder structure.
        os.symlink(os.environ['WEIGHTS_FOLDER'], os.path.join(out_dir, 'nnUNet'))
        
        # NOTE: instead of running from commandline this could also be done in a pythonic way:
        #       `nnUNet/nnunet/inference/predict.py` - but it would require
        #       to set manually all the arguments that the user is not intended
        #       to fiddle with; so stick with the bash executable

        # construct nnunet inference command
        bash_command  = ["nnUNet_predict"]
        bash_command += ["--input_folder", str(inp_dir)]
        bash_command += ["--output_folder", str(out_dir)]
        bash_command += ["--task_name", self.nnunet_task]
        bash_command += ["--model", self.nnunet_model]
        
        # add optional arguments
        if self.c and 'use_tta' in self.c and not self.c['use_tta']:
            bash_command += ["--disable_tta"]
        
        if self.c and 'export_prob_maps' in self.c and not self.c['export_prob_maps']:
            bash_command += ["--save_npz"]

        # run command
        bash_return = subprocess.run(bash_command, check=True, text=True)

        # output meta
        meta = {
            "model": "nnunet",
            "task": self.nnunet_task
        }

        # get output data
        out_file = f'VOLUME_001.nii.gz'
        out_path = os.path.join(out_dir, out_file)
        
        # add output data to instance
        data = InstanceData(out_path, DataType(FileType.NIFTI, SEG + meta))
        data.dc.makeEntrypoint()
        instance.addData(data)
