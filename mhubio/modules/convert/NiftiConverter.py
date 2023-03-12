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
from typing import Optional

from .DataConverter import DataConverter
from mhubio.core import Instance, InstanceData, DataType, FileType

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

    @property
    def engine(self) -> NiftiConverterEngine:
        if not hasattr(self, '_engine') or self._engine is None: # type: ignore
            engine_from_config = self.getConfiguration('engine', 'plastimatch')
            return NiftiConverterEngine[engine_from_config.upper()]
        else:
            return self._engine # type: ignore

    @engine.setter
    def engine(self, engine: NiftiConverterEngine) -> None:
        self._engine = engine

    def dicom2nifti_plastimatch(self, instance: Instance) -> Optional[InstanceData]:
        
        # cretae a converted instance
        assert instance.hasType(DataType(FileType.DICOM)), f"CONVERT ERROR: required datatype (dicom) not available in instance {str(instance)}."
        dicom_data = instance.getData(DataType(FileType.DICOM))

        # out data
        nifti_data = InstanceData("image.nii.gz", DataType(FileType.NIFTI, dicom_data.type.meta))
        nifti_data.instance = instance

        # log data
        log_data = InstanceData("_pypla.log", DataType(FileType.LOG, {
            "origin" : "plastimatch",
            "caller" : "NiftiConverter.dicom2nifti",
            "instance" : str(instance)
        }), instance)

        # paths
        inp_dicom_dir = dicom_data.abspath
        out_nifti_file = nifti_data.abspath
        out_log_file = log_data.abspath

        # sanity check
        assert(os.path.isdir(inp_dicom_dir))

        # DICOM CT to NRRD conversion (if the file doesn't exist yet)
        if os.path.isfile(out_nifti_file):
            print("CONVERT ERROR: File already exists: ", out_nifti_file)
            return None
        else:
            convert_args_ct = {
                "input" : inp_dicom_dir,
                "output-img" : out_nifti_file
            }

            # remove old log file if it exist
            if os.path.isfile(out_log_file): 
                os.remove(out_log_file)
            
            # run conversion using plastimatch
            pypla.convert(
                verbose=self.verbose,
                path_to_log_file=out_log_file,
                **convert_args_ct
            )

            return nifti_data
    
    def dicom2nifti_dcm2nii(self, instance: Instance) -> Optional[InstanceData]:

        assert instance.hasType(DataType(FileType.DICOM)), f"CONVERT ERROR: required datatype (dicom) not available in instance {str(instance)}."
        dicom_data = instance.getData(DataType(FileType.DICOM))

        # out data
        nifti_data = InstanceData("image.nii.gz", DataType(FileType.NIFTI, dicom_data.type.meta))
        nifti_data.instance = instance

        # paths
        inp_dicom_dir = dicom_data.abspath
        out_nifti_file = nifti_data.abspath

        # sanity check
        assert(os.path.isdir(inp_dicom_dir))

        # DICOM CT to NRRD conversion (if the file doesn't exist yet)
        # TODO: how do we handle existing files? 
        #       In theory, they should not exyist (we're in a not mounted folder inside Docker container...) 
        if os.path.isfile(out_nifti_file):
            print("CONVERT ERROR: File already exists: ", out_nifti_file)
            return None
        else:

            # verbosity level
            # TODO: once global verbosity levels are implemented, propagate them here
            if self.config.debug: 
                verbosity = 2
            elif self.config.verbose: 
                verbosity = 1
            else:
                verbosity = 0

            # build command
            # manual: https://www.nitrc.org/plugins/mwiki/index.php/dcm2nii:MainPage#General_Usage
            bash_command  = ["dcm2niix"]
            bash_command += ["-o", os.path.dirname(out_nifti_file)]         # output folder
            bash_command += ["-f", os.path.basename(out_nifti_file)[:-7]]   # output file name (pattern, but we handle a single dicom series as input)
            bash_command += ["-v", str(verbosity)]                          # verbosity
            bash_command += ["-z", "y"]                                     # output compression      
            bash_command += ["-b", "n"]                                     # do not generate a Brain Imaging Data Structure file      
            bash_command += [inp_dicom_dir]                                 # input folder (dicom) 

            # print run
            # TODO: implement global verbosity levels. This is required for debugging and has educational value.
            self.v(">> run: ", " ".join(bash_command))

            # execute command
            _ = subprocess.run(bash_command, check = True, text = True)

            return nifti_data

    def nrrd2nifti(self, instance: Instance) -> Optional[InstanceData]:
         
        assert instance.hasType(DataType(FileType.NRRD)), f"CONVERT ERROR: required datatype (nrrd) not available in instance {str(instance)}."
        nrrd_data = instance.getData(DataType(FileType.NRRD))

        # out data
        nifti_data = InstanceData("image.nii.gz", DataType(FileType.NIFTI, nrrd_data.type.meta))
        nifti_data.instance = instance

        # paths
        inp_nrrd_file = nrrd_data.abspath
        out_nifti_file = nifti_data.abspath
        out_log_file = os.path.join(instance.abspath, "_pypla.log")

        # sanity check
        assert(os.path.isfile(inp_nrrd_file))

        # DICOM CT to NRRD conversion (if the file doesn't exist yet)
        if os.path.isfile(out_nifti_file):
            print("CONVERT ERROR: File already exists: ", out_nifti_file)
            return None
        else:
            convert_args_ct = {
                "input" : inp_nrrd_file,
                "output-img" : out_nifti_file
            }

            # clean old log file if it exist
            if os.path.isfile(out_log_file): 
                os.remove(out_log_file)
            
            # run conversion using plastimatch
            pypla.convert(
                verbose=self.verbose,
                path_to_log_file=out_log_file,
                **convert_args_ct
            )

            return nifti_data
    
    def convert(self, instance: Instance) -> Optional[InstanceData]:

        hasDicom = instance.hasType(DataType(FileType.DICOM))
        hasNrrd = instance.hasType(DataType(FileType.NRRD))

        if hasDicom:
            if self.engine == NiftiConverterEngine.PLASTIMATCH:
                return self.dicom2nifti_plastimatch(instance)
            elif self.engine == NiftiConverterEngine.DCM2NIIX:
                return self.dicom2nifti_dcm2nii(instance)
            else:
                raise ValueError(f"CONVERT ERROR: unknown engine {self.engine}.")
        elif hasNrrd:
            return self.nrrd2nifti(instance)
        else:
            raise TypeError(f"CONVERT ERROR: required datatype (dicom or nrrd) not available in instance {str(instance)}.")
        