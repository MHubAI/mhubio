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
from .DataTypeQuery import DataTypeQuery
from .FileType import FileType
from .Meta import Meta
from .Error import MHubMissingDataError

class InstanceDataCollection:

    def __init__(self, data: Optional[List[InstanceData]] = None) -> None:
        self._data: List[InstanceData] = data or []
  
    @staticmethod
    def filterByDataType(pool: List['InstanceData'], ref_type: DataType, confirmed_only: bool = True) -> List['InstanceData']: 
        """
        Filter for instance data by a reference data type. Only instance data that match the file type and specified meta data of the reference type are returned. A datatype matches the reference type, if all metadata of the reference type is equal to the datatype. If a datatype contains additional meta data compared to the reference type (specialization) those additional keys are ignored. 
        """

        # collect only instance data passing all checks (ftype, meta)
        matching_data: List[InstanceData] = []

        # iterate all instance data of this instance
        for data in pool:
            # check if data is confirmed
            if confirmed_only and not data.confirmed:
                continue

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
    
    @classmethod
    def filterByString(cls, pool: List['InstanceData'], ref_type: str, confirmed_only: bool = True) -> List['InstanceData']:
        return cls.filterByDataType(pool, DataType.fromString(ref_type), confirmed_only)

    def filter(self, ref_types: Union[DataType, str, List[DataType], List[str], DataTypeQuery], confirmed_only: bool = False) -> 'InstanceDataCollection':
        if isinstance(ref_types, list) or isinstance(ref_types, DataType): 
            print("\033[95mDEPRECATION WARNING: InstanceDataCollection.filter() should be called with a DataTypeQuery instance or DataTypeQuery compatible string.\033[0m")

        if isinstance(ref_types, DataTypeQuery):
            return InstanceDataCollection([d for d in self._data if (d.confirmed or not confirmed_only) and ref_types.exec(d.type)])
        elif isinstance(ref_types, str):
            dtq = DataTypeQuery(ref_types)
            return InstanceDataCollection([d for d in self._data if (d.confirmed or not confirmed_only) and dtq.exec(d.type)])
            #ref_types = [ref_types]
        elif isinstance(ref_types, DataType):
            ref_types = [ref_types]
        
        # convert string representations to DataType instances
        ref_types = [DataType.fromString(ref_type) if isinstance(ref_type, str) else ref_type for ref_type in ref_types]

        # filter by data type
        return InstanceDataCollection(list(set(sum([self.filterByDataType(self._data, ref_type, confirmed_only) for ref_type in ref_types], []))))

    def ask(self, i: int) -> Optional[InstanceData]:
        if i < 0 or i >= len(self._data):
            return None
        return self._data[i]
    
    def get(self, i: int) -> InstanceData:
        if i < 0 or i >= len(self._data):
            raise MHubMissingDataError(f"Requested data (index {i}) does not exist.")
        return self._data[i]

    def first(self, ref_types: Optional[Union[DataType, str, List[DataType], List[str], DataTypeQuery]] = None, confirmed_only: bool = False) -> InstanceData:
        if ref_types is not None:
            idc = self.filter(ref_types, confirmed_only)
        else:
            idc = self

        if not len(idc) and ref_types is None:
            raise MHubMissingDataError("No data.")
        elif not len(idc):
            raise MHubMissingDataError(f"No data matching {ref_types}.")
        
        return idc.get(0)

    def asList(self) -> List[InstanceData]:
        return self._data
    
    def add(self, data: InstanceData) -> None:
        if not data in self._data:
            self._data.append(data)

    def sort(self):
        """sorting all instacne data (files) by their absolute path"""
        self._data.sort(key=lambda d: d.abspath)

    def __len__(self) -> int:
        return len(self._data)
    
    def __elem__(self, data: InstanceData) -> bool:
        return data in self._data
    
    def __iter__(self) -> 'InstanceDataCollectionIterator':
        return InstanceDataCollectionIterator(self)

class InstanceDataCollectionIterator:
    def __init__(self, collection: InstanceDataCollection) -> None:
        self._collection: InstanceDataCollection = collection
        self._index: int = 0

    def __iter__(self) -> 'InstanceDataCollectionIterator':
        return self
    
    def __next__(self) -> InstanceData:
        if self._index >= len(self._collection):
            raise StopIteration
        data = self._collection.get(self._index)
        self._index += 1
        return data