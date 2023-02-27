"""
-------------------------------------------------
MHub - File type class for mhubio instance data
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (27.02.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from enum import Enum

class FileType(Enum):
    NONE = None
    NRRD = "nrrd"
    NIFTI = "nifti"
    DICOM = "dicom"
    DICOMSEG = "dicomseg"
    RTSTRUCT = "RTSTRUCT"

    def __str__(self) -> str:
        return self.name