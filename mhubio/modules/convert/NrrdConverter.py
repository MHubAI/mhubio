"""
-------------------------------------------------
MHub - Dicom2Nrrd Conversion Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""


from typing import Optional

from .DataConverter import DataConverter
from mhubio.core import Instance, InstanceData, DataType, FileType

import os
import pyplastimatch as pypla # type: ignore

class NrrdConverter(DataConverter):
    """
    Conversion module. 
    Convert instance data from dicom to nrrd.
    """
    
    def convert(self, instance: Instance) -> Optional[InstanceData]:

        # cretae a converted instance
        assert instance.hasType(DataType(FileType.DICOM)), f"CONVERT ERROR: required datatype (dicom) not available in instance {str(instance)}."
        dicom_data = instance.getData(DataType(FileType.DICOM))

        # out data
        nrrd_data = InstanceData("image.nrrd", DataType(FileType.NRRD, dicom_data.type.meta))
        nrrd_data.instance = instance

        # paths
        inp_dicom_dir = dicom_data.abspath
        out_nrrd_file = nrrd_data.abspath
        out_log_file = os.path.join(instance.abspath, "_pypla.log")

        # sanity check
        assert(os.path.isdir(inp_dicom_dir))

        # DICOM CT to NRRD conversion (if the file doesn't exist yet)
        if os.path.isfile(out_nrrd_file):
            print("CONVERT ERROR: File already exists: ", out_nrrd_file)
            return None
        else:
            convert_args_ct = {
                "input" : inp_dicom_dir,
                "output-img" : out_nrrd_file
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

            return nrrd_data
    