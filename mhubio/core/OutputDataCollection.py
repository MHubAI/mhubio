"""
-------------------------------------------------
MHub - Collection of Instance Data
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import Optional, Union, List
from .RunnerOutput import RunnerOutput
from .DataTypeQuery import DataTypeQuery
from .Error import MHubMissingDataError

class OutputDataCollection:

    def __init__(self, data: Optional[List[RunnerOutput]] = None) -> None:
        self._data: List[RunnerOutput] = data or []
  
    # TODO: simplify the current InstanceDataCollection to this interface
    # def filter(self, dtq: DataTypeQuery, confirmed_only: bool = False) -> 'InstanceDataCollection':
    #   match = dtq.filter(self._data)
    #   if confirmed_only: match = [d for d in match if d.confirmed]
    #   return InstanceDataCollection(match)
    def filter(self, dtq: Union[str, DataTypeQuery]) -> 'OutputDataCollection':
        if isinstance(dtq, str):
            dtq = DataTypeQuery(dtq)
        return OutputDataCollection(dtq.filter(self._data))

    def ask(self, i: int) -> Optional[RunnerOutput]:
        if i < 0 or i >= len(self._data):
            return None
        return self._data[i]
    
    def get(self, i: int) -> RunnerOutput:
        if i < 0 or i >= len(self._data):
            raise MHubMissingDataError(f"Requested output data (index {i}) does not exist.")
        return self._data[i]

    # TODO: simplify in InstacneDataColelction analog to thi implementatio (see above, include confirmed only flag)
    def first(self, dtq: Optional[DataTypeQuery] = None) -> RunnerOutput:
        if dtq is not None:
            idc = self.filter(dtq)
        else:
            idc = self

        if not len(idc) and dtq is None:
            raise MHubMissingDataError("No data.")
        elif not len(idc):
            raise MHubMissingDataError(f"No data matching {str(dtq)}.")
        
        return idc.get(0)

    def asList(self) -> List[RunnerOutput]:
        return self._data
    
    def add(self, data: RunnerOutput) -> None:
        if not data in self._data:
            self._data.append(data)

    def sort(self):
        """sorting all output data by name"""
        self._data.sort(key=lambda d: d.name)

    def __len__(self) -> int:
        return len(self._data)
    
    def __elem__(self, data: RunnerOutput) -> bool:
        return data in self._data
    
    def __iter__(self) -> 'OutputDataCollectionIterator':
        return OutputDataCollectionIterator(self)

class OutputDataCollectionIterator:
    def __init__(self, collection: OutputDataCollection) -> None:
        self._collection: OutputDataCollection = collection
        self._index: int = 0

    def __iter__(self) -> 'OutputDataCollectionIterator':
        return self
    
    def __next__(self) -> RunnerOutput:
        if self._index >= len(self._collection):
            raise StopIteration
        data = self._collection.get(self._index)
        self._index += 1
        return data