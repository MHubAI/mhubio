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

    @staticmethod
    def fromString(s: str) -> 'DataType':
        """
        Convert data in form $file_type:$meta_key1=$meta_value1:$meta_key2=$meta_value2 to DataType instance.
        Example: DICOMSEG:mod=seg -> DataType(FileType.DICOMSEG, Meta(mod, seg))
        """

        # extract file type and meta key value paris
        ftype_def, *meta_def = s.split(":")

        # get file type
        ftype_def = ftype_def.upper()
        assert ftype_def in FileType.__members__, f"{ftype_def} not a valid file type."
        ftype = FileType[ftype_def]

        # assemple meta dictionary
        meta_dict: Dict[str, str] = {}
        for kvp in meta_def:
            key, value = kvp.split("=")
            meta_dict[key] = value

        # convert to meta instance
        meta = Meta() + meta_dict

        # create data type instance
        return DataType(ftype, meta)

    def toString(self) -> str:
        """
        Convert data type to string representation.
        Example: DataType(FileType.DICOMSEG, Meta(mod, seg)) -> DICOMSEG:mod=seg
        """

        # assemble meta string
        meta_str = ":".join([f"{k}={v}" for k, v in self.meta.items()])

        # assemble data type string
        return f"{self.ftype.name}:{meta_str}"

    def __str__(self) -> str:
        s: str = "[T:" + str(self.ftype)
        if self.meta: s += ":" + str(self.meta)
        s += "]"
        return s