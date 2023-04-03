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
    # _data:        InstanceDataCollection
    # attr:         Dict[str, str]

    def __init__(self, path: str = "") -> None:
        super().__init__(path=path, parent=None, base=None)
        self._handler: Optional['DataHandler'] = None                   # NOTE: handler is set delayed but is NOT OPTIONAL !
        self.data: InstanceDataCollection = InstanceDataCollection()
        self.attr: Dict[str, str] = {'id': str(uuid.uuid4())}

    @property
    def handler(self) -> 'DataHandler':
        assert self._handler is not None
        return self._handler
    
    @handler.setter
    def handler(self, handler: 'DataHandler'):
        self._handler = handler
        self.dc.setParent(handler.dc)

    def hasType(self, type: DataType) -> bool:
        return len([d for d in self.data if d.type.ftype == type.ftype]) > 0 # FIXME: need proper matching!!! 

    def getDataMetaKeys(self) -> List[str]:
        return list(set(sum([list(d.type.meta.keys()) for d in self.data], [])))

    def printDataOverview(self, idc: Optional['InstanceDataCollection'] = None, meta: bool = False, label: str = "") -> None:

        # you may specify data explicitly (e.g. the result of a filter), otherwise we use the instance's data
        if idc is None:
            idc = self.data

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
        for data in idc:
            print(f"├── {chead}{str(data.type.ftype)}{cend} [{data.abspath}]", u'\u2713' if data.confirmed else u'\u2717')

            # print meta    
            if meta:
                for k, v in data.type.meta.items():
                    print(f"│   ├── {cyan}{k}: {v}{cend}")

    def printDataMetaOverview(self, idc: Optional['InstanceDataCollection'] = None, compress: bool = True, label: str = "") -> None:

        # you may specify data explicitly (e.g. the result of a filter), otherwise we use the instance's data
        if idc is None:
            idc = self.data
               
        # count
        cnt: Dict[FileType, Dict[str, Dict[str, int]]] = {}
        cnt_ftype: Dict[FileType, int] = {}

        for data in idc:

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

    def addData(self, data: 'InstanceData') -> None:

        # set instance reference
        data.instance = self
        
        # print a warning if data was already added to instance
        if data in self.data:
           print("WARNING: data was already added to instance.")
           return

        # add data to collection (no duplicates)
        self.data.add(data)

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
from .InstanceDataCollection import InstanceDataCollection