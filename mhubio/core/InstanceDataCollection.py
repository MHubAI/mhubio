"""
-------------------------------------------------
MHub - Collection of Instance Data
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import Optional, Union, Dict, List, Tuple, Any
from .InstanceData import InstanceData
from .DataType import DataType
from .FileType import FileType
from .Meta import Meta

class InstanceDataCollection:

    def __init__(self, data: List[InstanceData]) -> None:
        self._data: List[InstanceData] = data
  
    @staticmethod
    def convertStringToDataType(s: str) -> DataType:
        """
        Convert data in form $file_type:$meta_key1=$meta_value1:$meta_key2=$meta_value2 to DataType instance.
        Example: DICOMSEG:mod=seg -> DataType(FileType.DICOMSEG, Meta(mod, seg))
        """

        # extract file type and meta key value paris
        ftype_def, *meta_def = s.split(":")

        # get file type
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

    @staticmethod
    def filterByDataType(pool: List['InstanceData'], ref_type: DataType) -> List['InstanceData']: 
        """
        Filter for instance data by a reference data type. Only instance data that match the file type and specified meta data of the reference type are returned. A datatype matches the reference type, if all metadata of the reference type is equal to the datatype. If a datatype contains additional meta data compared to the reference type (specialization) those additional keys are ignored. 
        """

        # collect only instance data passing all checks (ftype, meta)
        matching_data: List[InstanceData] = []

        # iterate all instance data of this instance
        for data in pool:
            # check file type, ignore other filetypes
            if ref_type.ftype is not FileType.NONE and not data.type.ftype == ref_type.ftype:
                continue

            # check if metadata is less general than ref_type's metadata
            if not data.type.meta <= ref_type.meta:
                continue
          
            # add instance data that passes all prior checks
            matching_data.append(data)

        # return matches
        return matching_data
    
    @staticmethod
    def filterByString(pool: List['InstanceData'], ref_type: str) -> List['InstanceData']:
        return InstanceDataCollection.filterByDataType(pool, InstanceDataCollection.convertStringToDataType(ref_type))

    def filter(self, ref_types: Union[DataType, str, List[DataType], List[str]]) -> 'InstanceDataCollection':
        if isinstance(ref_types, str):
            ref_types = [ref_types]
        elif isinstance(ref_types, DataType):
            ref_types = [ref_types]
        
        # convert string representations to DataType instances
        ref_types = [InstanceDataCollection.convertStringToDataType(ref_type) if isinstance(ref_type, str) else ref_type for ref_type in ref_types]

        # filter by data type
        return InstanceDataCollection(list(set(sum([InstanceDataCollection.filterByDataType(self._data, ref_type) for ref_type in ref_types], []))))

    def asList(self) -> List[InstanceData]:
        return self._data
    
    def add(self, data: InstanceData) -> None:
        if not data in self._data:
            self._data.append(data)

    def __len__(self) -> int:
        return len(self._data)