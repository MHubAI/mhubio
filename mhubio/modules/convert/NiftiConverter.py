"""
-------------------------------------------------
MHub - Nifti Conversion Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""


from enum import Enum
from typing import Optional, List

from .DataConverter import DataConverter
from mhubio.core import Config, Instance, InstanceDataBundle, InstanceDataCollection, InstanceData, DataType, FileType, CT

import os, subprocess
import pyplastimatch as pypla # type: ignore

class NiftiConverterEngine(Enum):
    PLASTIMATCH = 'plastimatch'
    DCM2NIIX     = 'dcm2niix'

class NiftiConverter(DataConverter):
    """
    Conversion module. 
    Convert instance data from dicom or nrrd to nifti.
    """

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._engine: Optional[NiftiConverterEngine] = None
        self._allow_multi_input: Optional[bool] = None
        self._targets: List[DataType] = []

        self._importTargetsFromConfig()

    @property
    def engine(self) -> NiftiConverterEngine:
        if self._engine is None: 
            engine_from_config = self.getConfiguration('engine', 'plastimatch')
            return NiftiConverterEngine[engine_from_config.upper()]
        else:
            return self._engine 

    @engine.setter
    def engine(self, engine: NiftiConverterEngine) -> None:
        self._engine = engine

    @property
    def allow_multi_input(self) -> bool:
        if self._allow_multi_input is None:
            return self.getConfiguration('allow_multi_input', False)
        else:
            return self._allow_multi_input
        
    @allow_multi_input.setter
    def allow_multi_input(self, allow_multi_input: bool) -> None:
        self._allow_multi_input = allow_multi_input  

    def _importTargetsFromConfig(self) -> None:
        """
        conversion example [code implementation / config dictionary]  
        restricted characters: [':', '=']

        converter.setTarget(DataType(FileType.DICOM, Meta(part='ADC')))
        converter.setTarget(DataType(FileType.DICOM, Meta(part='T2')))

        {
          "modules": {
              "NiftiConverter": {
                  "targets": [
                      "DICOM:part=ADC",   
                      "DICOM:part=T2"
                  ]
             }
        }
        """

        # automatically import targets from config if defined
        targets = self.getConfiguration("targets")
        if targets and isinstance(targets, list):
            for target_definition in targets:
                try:
                    # instantiate datatype from string representation
                    data_type = DataType.fromString(target_definition)
                    
                    # set target 
                    self.setTarget(data_type)
                except Exception as e:
                    print(f"WARNING: could not parse target definition '{target_definition}: {str(e)}'")

    def setTarget(self, target: DataType) -> None:
        self._targets.append(target)

    def plastimatch(self, instance: Instance, in_data: InstanceData, out_data: InstanceData, bundle: Optional[InstanceDataBundle] = None) -> None:

        # log data
        log_data = InstanceData("_pypla.log", DataType(FileType.LOG, {
            "origin" : "plastimatch",
            "caller" : "NiftiConverter.dicom2nifti",
            "instance" : str(instance)
        }), instance)

        if bundle:
            bundle.addData(log_data)

        # set input and output paths later passed to plastimatch
        convert_args_ct = {
            "input" : in_data.abspath,
            "output-img" : out_data.abspath
        }

        # remove old log file if it exist
        if os.path.isfile(log_data.abspath): 
            os.remove(log_data.abspath)
        
        # run conversion using plastimatch
        pypla.convert(
            verbose=self.verbose,
            path_to_log_file=log_data.abspath,
            **convert_args_ct
        )

    def dcm2nii(self, instance: Instance, in_data: InstanceData, out_data: InstanceData) -> None:

        # verbosity level
        # TODO: once global verbosity levels are implemented, propagate them here
        if self.config.debug: 
            verbosity = 2
        elif self.config.verbose: 
            verbosity = 1
        else:
            verbosity = 0

        # get folder and file name as dcm2niix takes two separate arguments
        assert out_data.abspath.endswith(".nii.gz")
        out_data_dir = os.path.dirname(out_data.abspath)
        out_data_file = os.path.basename(out_data.abspath)[:-7]

        # build command
        # manual: https://www.nitrc.org/plugins/mwiki/index.php/dcm2nii:MainPage#General_Usage
        bash_command  = ["dcm2niix"]
        bash_command += ["-o", out_data_dir]        # output folder
        bash_command += ["-f", out_data_file]       # output file name (pattern, but we handle a single dicom series as input)
        bash_command += ["-v", str(verbosity)]      # verbosity
        bash_command += ["-z", "y"]                 # output compression      
        bash_command += ["-b", "n"]                 # do not generate a Brain Imaging Data Structure file      
        bash_command += [in_data.abspath]           # input folder (dicom) 

        # print run
        # TODO: implement global verbosity levels. This is required for debugging and has educational value.
        self.v(">> run: ", " ".join(bash_command))

        # execute command
        _ = subprocess.run(bash_command, check = True, text = True)

    def convert(self, instance: Instance) -> None:

        # define output semantics
        converted_file_name: str = self.getConfiguration('converted_file_name', 'image.nii.gz')
        bundle_name: Optional[str] = self.getConfiguration('bundle_name', None)   # will be set as bundle ref

        # experimental
        if bundle_name is not None:
            print("WARNING: experimental feature 'bundle_name' is used.")

        # define default targets
        default_targets = [
            DataType(FileType.DICOM, CT),
            DataType(FileType.NRRD, CT),
        ]

        # fetch target data from instance (use default targets if nothing else specified)
        targets = self._targets if len(self._targets) > 0 else default_targets

        # debug  
        # print("--->", len(targets), str([str(dt) for dt in targets]))

        # filter instance for data
        idc = InstanceDataCollection(instance.data)
        target_idc = idc.filter(targets)

        # check if filtered collection contains at least one data
        assert len(target_idc) > 0, f"CONVERT ERROR: no data found in instance {str(instance)}."

        # check if multi file conversion is enables
        # TODO: consider removing this limitation
        in_datas = target_idc.asList()
        if not self.allow_multi_input and len(in_datas) > 1:
            print("WARNING: found more than one matching file but multi file conversion is disabled. Only the first file will be converted.")
            in_datas = [in_datas[0]]

        # conversion step
        for in_data in in_datas:

            # get output data
            out_data = InstanceData(converted_file_name, DataType(FileType.NIFTI, in_data.type.meta))
            out_data.instance = instance

            # check if output data already exists
            if os.path.isfile(out_data.abspath) and not self.getConfiguration('overwrite_existing_file', False):
                print("CONVERT ERROR: File already exists: ", out_data.abspath)
                continue

            # create bundle
            bundle: Optional[InstanceDataBundle] = in_data.bundle
            if bundle_name is not None:
                bundle = in_data.getDataBundle(bundle_name)         # NOTE: if in_data has a bundle, this will automatically expand on that bundle

            # check datatype 
            if in_data.type.ftype == FileType.DICOM:

                # for dicom data use either plastimatch or dcm2niix 
                if self.engine == NiftiConverterEngine.PLASTIMATCH:
                    self.plastimatch(instance, in_data, out_data, bundle)
                elif self.engine == NiftiConverterEngine.DCM2NIIX:
                    self.dcm2nii(instance, in_data, out_data)
                else:
                    raise ValueError(f"CONVERT ERROR: unknown engine {self.engine}.")
            elif in_data.type.ftype == FileType.NRRD:

                # for nrrd files use plastimatch
                self.plastimatch(instance, in_data, out_data, bundle)

            # check if output file was created
            if not os.path.isfile(out_data.abspath):
                print("CONVERT ERROR: File not created: ", out_data.abspath)
                continue

            # add output data to bundle or instance
            if bundle:
                bundle.addData(out_data)
            else:
                instance.addData(out_data)