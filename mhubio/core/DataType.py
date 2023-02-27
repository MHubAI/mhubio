"""
-------------------------------------------------
MHub - Data type class for mhubio instance data
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (27.02.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import Optional
from .FileType import FileType
from .Meta import Meta

class DataType:
    def __init__(self, ftype: FileType, meta: Optional[Meta] = None) -> None:
        self.ftype: FileType = ftype
        self.meta: Meta = meta if meta else Meta()

    def __str__(self) -> str:
        s: str = "[T:" + str(self.ftype)
        if self.meta: s += ":" + str(self.meta)
        s += "]"
        return s