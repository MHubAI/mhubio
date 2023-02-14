"""
-------------------------------------------------
MHub - Nifti Conversion Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""


from typing import Optional

from .DataConverter import DataConverter
from mhubio.Config import Instance, InstanceData, DataType, FileType

import os
import pyplastimatch as pypla # type: ignore

class NiftiConverter(DataConverter):
    """
    Conversion module. 
    Convert instance data from dicom or nrrd to nifti.
    """

    def dicom2nifti(self, instance: Instance) -> Optional[InstanceData]:
        
        # cretae a converted instance
        assert instance.hasType(DataType(FileType.DICOM)), f"CONVERT ERROR: required datatype (dicom) not available in instance {str(instance)}."
        dicom_data = instance.getData(DataType(FileType.DICOM))

        # out data
        nifti_data = InstanceData("image.nii.gz", DataType(FileType.NIFTI, dicom_data.type.meta))
        nifti_data.instance = instance

        # paths
        inp_dicom_dir = dicom_data.abspath
        out_nifti_file = nifti_data.abspath
        out_log_file = os.path.join(instance.abspath, "_pypla.log")

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
    
    def nrrd2nifti(self, instance: Instance) -> Optional[InstanceData]:
         
        # cretae a converted instance
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
            return self.dicom2nifti(instance)
        elif hasNrrd:
            return self.nrrd2nifti(instance)
        else:
            raise TypeError(f"CONVERT ERROR: required datatype (dicom or nrrd) not available in instance {str(instance)}.")