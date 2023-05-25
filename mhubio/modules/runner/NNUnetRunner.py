"""
-------------------------------------------------
MHub - NNU-Net Runner
       This is a base runner for pre-trained 
       nnunet models. 
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""
# TODO: support multi-i/o and batch processing on multiple instances

import os, subprocess, shutil
from mhubio.core import Module, Instance, InstanceData, DataType, FileType, IO

# TODO: add an optional evaluation pattern (regex) to IO.Config
nnunet_task_name_regex = r"Task[0-9]{3}_[a-zA-Z0-9_]+"

@IO.Config('nnunet_task', str, None, the='nnunet task name')
@IO.Config('nnunet_model', str, None, the='nnunet model name (2d, 3d_lowres, 3d_fullres, 3d_cascade_fullres)')
@IO.Config('input_data_type', DataType, 'nifti:mod=ct', factory=DataType.fromString, the='input data type')
@IO.Config('folds', int, None, the='number of folds to run nnunet on')
@IO.Config('use_tta', bool, False, the='flag to enable test time augmentation')
@IO.Config('export_prob_maps', bool, False, the='flag to export probability maps')
@IO.Config('roi', str, None, the='roi or comma separated list of roi the nnunet segments')
class NNUnetRunner(Module):

    nnunet_task: str
    nnunet_model: str
    input_data_type: DataType
    folds: int                          # TODO: support optional config attributes
    use_tta: bool
    export_prob_maps: bool
    roi: str

    @IO.Instance()
    @IO.Input("in_data", IO.C("input_data_type"), the="input data to run nnunet on")
    @IO.Output("out_data", 'VOLUME_001.nii.gz', 'nifti:mod=seg:model=nnunet', data='in_data', the="output data from nnunet")
    def task(self, instance: Instance, in_data: InstanceData, out_data: InstanceData) -> None:
        
        # get the nnunet model to run
        self.v("Running nnUNet_predict.")
        self.v(f" > task:        {self.nnunet_task}")
        self.v(f" > model:       {self.nnunet_model}")
        self.v(f" > input data:  {in_data.abspath}")
        self.v(f" > output data: {out_data.abspath}")

        # download weights if not found
        # NOTE: only for testing / debugging. For productiio always provide the weights in the Docker container.
        if not os.path.isdir(os.path.join(os.environ["WEIGHTS_FOLDER"], '')):
            print("Downloading nnUNet model weights...")
            bash_command = ["nnUNet_download_pretrained_model", self.nnunet_task]
            _ = subprocess.run(bash_command, stdout=subprocess.PIPE)

        # bring input data in nnunet specific format
        # NOTE: only for nifti data as we hardcode the nnunet-formatted-filename (and extension) for now.
        assert in_data.type.ftype == FileType.NIFTI
        assert in_data.abspath.endswith('.nii.gz')
        inp_dir = self.config.data.requestTempDir(label="nnunet-model-inp")
        inp_file = f'VOLUME_001_0000.nii.gz'
        shutil.copyfile(in_data.abspath, os.path.join(inp_dir, inp_file))

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
        if self.folds is not None:
            bash_command += ["--folds", str(self.folds)]

        if self.use_tta:
            bash_command += ["--disable_tta"]
        
        if self.export_prob_maps:
            bash_command += ["--save_npz"]

        # run command
        _ = subprocess.run(bash_command, check=True, text=True)

        # output meta
        meta = {
            "model": "nnunet",
            "nnunet_task": self.nnunet_task,
            "nnunet_model": self.nnunet_model,
            "roi": self.roi
        }

        # get output data
        out_file = f'VOLUME_001.nii.gz'
        out_path = os.path.join(out_dir, out_file)

        # copy output data to instance
        shutil.copyfile(out_path, out_data.abspath)

        # update meta dynamically
        out_data.type.meta += meta

        # confirm output data
        if os.path.isfile(out_data.abspath):
            out_data.confirm()
