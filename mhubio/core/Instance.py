"""
-------------------------------------------------
MHub - Instance class for mhubio framwork
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (27.02.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

import os, uuid

from typing import List, Dict, Optional, Union
from .DataType import DataType
from .FileType import FileType
from .DirectoryChain import DirectoryChainInterface

class Instance(DirectoryChainInterface): 
    # handler:      DataHandler
    # path:         str
    # _data:        List[InstanceData]
    # attr:         Dict[str, str]

    def __init__(self, path: str = "") -> None:
        super().__init__(path=path, parent=None, base=None)
        self._handler: Optional['DataHandler'] = None            # NOTE: handler is set delayed but is NOT OPTIONAL !
        self._data: List['InstanceData'] = []
        self.attr: Dict[str, str] = {'id': str(uuid.uuid4())}

    @property
    def handler(self) -> 'DataHandler':
        assert self._handler is not None
        return self._handler
    
    @handler.setter
    def handler(self, handler: 'DataHandler'):
        self._handler = handler
        self.dc.setParent(handler.dc)

    @property
    def data(self) -> List['InstanceData']:
        return self._data

    @data.setter
    def data(self, data: List['InstanceData']):
        for d in data:
            d.instance = self
        self._data = data

    def hasType(self, type: DataType) -> bool:
        return len([d for d in self.data if d.type.ftype == type.ftype]) > 0 # FIXME: need proper matching!!! 

    def getDataMetaKeys(self) -> List[str]:
        return list(set(sum([list(d.type.meta.keys()) for d in self.data], [])))

    def printDataOverview(self, datas: Optional[List['InstanceData']] = None, meta: bool = False, label: str = "") -> None:

        # you may specify data explicitly (e.g. the result of a filter), otherwise we use the instance's data
        if datas is None:
            datas = self.data

        # formatting options
        # TODO: outsource or standardize if used frequently
        chead = '\033[95m'
        cyan = '\033[96m'
        cend = '\033[0m'
        fitalics = '\x1B[3m'
        fnormal ='\x1B[0m'

        # print fromatted output
        print(f". Instance {fitalics}{label}{fnormal} [{self.abspath}]")
        for k, v in self.attr.items():
            print(f"├── {cyan}{k}: {v}{cend}")
        for data in datas:
            print(f"├── {chead}{str(data.type.ftype)}{cend} [{data.abspath}]")

            # print meta    
            if meta:
                for k, v in data.type.meta.items():
                    print(f"│   ├── {cyan}{k}: {v}{cend}")

    def printDataMetaOverview(self, datas: Optional[List['InstanceData']] = None, compress: bool = True, label: str = "") -> None:

        # you may specify data explicitly (e.g. the result of a filter), otherwise we use the instance's data
        if datas is None:
            datas = self.data
               
        # count
        cnt: Dict[FileType, Dict[str, Dict[str, int]]] = {}
        cnt_ftype: Dict[FileType, int] = {}

        for data in datas:

            # count filetypes (regardless of meta presence)
            if not data.type.ftype in cnt_ftype: cnt_ftype[data.type.ftype] = 0
            cnt_ftype[data.type.ftype] += 1

            # count meta 
            for k, v in data.type.meta.items():
                if not data.type.ftype in cnt: cnt[data.type.ftype] = {}
                if not k in cnt[data.type.ftype]: cnt[data.type.ftype][k] = {}
                if not v in cnt[data.type.ftype][k]: cnt[data.type.ftype][k][v] = 0

                cnt[data.type.ftype][k][v] += 1

        # formatting options
        # TODO: outsource or standardize if used frequently
        chead = '\033[95m'
        cyan = '\033[96m'
        cend = '\033[0m'
        fitalics = '\x1B[3m'
        fnormal ='\x1B[0m'

        # get maximal terminal length or set a default length
        try:
            maxTerminalLength = os.get_terminal_size().columns
        except OSError as e:
            maxTerminalLength = 100

        # print fromatted output
        print(f". {fitalics}{label}{fnormal}")
        for ftype in cnt_ftype:
            print(f"├── {chead}{str(ftype)}{cend} [{cnt_ftype[ftype]}]")
            if not ftype in cnt: continue
            for k in cnt[ftype]:
                print(f"|   ├── {cyan}{k:<20}{cend}")
                for v, n in cnt[ftype][k].items():
                    if not compress or n > 1:
                        print(f"|   |   ├── ({n:<4}) {cyan}{v}{cend}")
                if compress:
                    n1lst = sorted([v for v, n in cnt[ftype][k].items() if n == 1])

                    if n1lst:
                        print(f"|   |   ├── ", end="")
                        
                        while n1lst:
                            cc = 12
                            while n1lst and cc + len(str(n1lst[0])) + 2 < maxTerminalLength:
                                print(str(n1lst[0]) + ", ", end="")
                                cc  += len(str(n1lst[0])) + 2
                                n1lst = n1lst[1:]
                            if n1lst:
                                print(f"\n|   |   |   ", end="")
                        print("")

    def filterData(self, ref_types: Union[DataType, List[DataType]]) -> List['InstanceData']:
        if not isinstance(ref_types, list):
            ref_types = [ref_types]
        return list(set(sum([self._filterData(ref_type) for ref_type in ref_types], [])))       

    def _filterData(self, ref_type: DataType) -> List['InstanceData']: 
        """
        Filter for instance data by a reference data type. Only instance data that match the file type and specified meta data of the reference type are returned. A datatype matches the reference type, if all metadata of the reference type is equal to the datatype. If a datatype contains additional meta data compared to the reference type (specialization) those additional keys are ignored. 
        """

        # collect only instance data passing all checks (ftype, meta)
        matching_data: List[InstanceData] = []

        # iterate all instance data of this instance
        for data in self.data:
            # check file type, ignore other filetypes
            if not data.type.ftype == ref_type.ftype:
                continue

            # check if metadata is less general than ref_type's metadata
            if not data.type.meta <= ref_type.meta:
                continue
          
            # add instance data that passes all prior checks
            matching_data.append(data)

        # return matches
        return matching_data

    def getData(self, ref_types: DataType) -> 'InstanceData':
        fdata = self.filterData(ref_types)

        # warning if multiple data available
        if len(fdata) > 1: 
            print("Warning, type is not unique. First element is returned.")
        
        #FIXME: when adding exception management, this should throw
        if len(fdata) == 0: 
            print("Ooops, no data found.")
            print("> You were asking for " + str(ref_types) + ". But all I have is:")
            print("> ", "\n> ".join([str(x) for x in self.data]))

        # return data
        return fdata[0]

    # TODO: make it possible to connect data and instance such that all paths are calculatedd correctly but the data is "invisible" to the instance (at salvo). Invoke a .complete() method to resolve. Technically, this can already be achived (although not as obvious to the reader) by first assigning th einstance to the data (data.instance = instance) but without adding th edata to the instance (which has to be done later a.k.a. resolving). We could, however, check if data has a diverging instance and in that case forbid adding (assert data.instance is None or self)
    # e.g. add , salvo: bool = False to addData signature
    def addData(self, data: 'InstanceData') -> None:
        data.instance = self
        
        if data not in self._data:
            self._data.append(data)
        else:
            print("WARNING: data was already added to instance.")

    def __str__(self) -> str:
        return "<I:%s>"%(self.abspath)
    
    def getDataBundle(self, ref: str) -> 'InstanceDataBundle':
        return InstanceDataBundle(ref=ref, instance=self)
    

class UnsortedInstance(Instance):
    def __init__(self, path: str = "") -> None:
        super().__init__(path)


class SortedInstance(Instance):
    def __init__(self, path: str = "") -> None:
        super().__init__(path)


from .DataHandler import DataHandler
from .InstanceData import InstanceData
from .InstanceDataBundle import InstanceDataBundle