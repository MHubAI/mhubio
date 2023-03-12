"""
-------------------------------------------------
MHub - Data type class for mhubio instance data
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (27.02.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import Optional, Union, Dict
from .FileType import FileType
from .Meta import Meta

class DataType:
    def __init__(self, ftype: FileType, meta: Optional[Union[Meta, Dict[str, str]]] = None) -> None:
        self.ftype: FileType = ftype

        if meta is None:
            self.meta: Meta = Meta()
        elif isinstance(meta, Meta):
            self.meta: Meta = meta
        elif isinstance(meta, dict):
            self.meta: Meta = Meta() + meta
        else:
            raise TypeError("Second argument of DataType must be of type Meta or Dict[str, str]")

    def __str__(self) -> str:
        s: str = "[T:" + str(self.ftype)
        if self.meta: s += ":" + str(self.meta)
        s += "]"
        return s