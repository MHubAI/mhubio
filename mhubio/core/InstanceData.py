"""
-------------------------------------------------
MHub - Instance data class for mhubio framework
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (27.02.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""
import os

from typing import Optional
from .DirectoryChain import DirectoryChainInterface
from .DataType import DataType

class InstanceData(DirectoryChainInterface):
    # instance:     Instance
    # type:         DataType
    # path:         str
    # base:         str
    
    def __init__(self, path: str, type: DataType, instance: Optional['Instance'] = None, bundle: Optional['InstanceDataBundle'] = None, data: Optional['InstanceData'] = None, auto_increment: bool = False) -> None:
        super().__init__(path=path, base=None, parent=None)
        self._instance: Optional[Instance] = None
        self._bundle: Optional[InstanceDataBundle] = None
        self._confirmed: bool = False
        self.type: DataType = type

        # create dual link d<->i based on passed reference data
        # although optional, it's best practice is to link InstanceData directly
        # hirarchy: bundle > data.bundle > instance > data.instance
        if bundle and isinstance(bundle, InstanceDataBundle):
            bundle.addData(self)
        elif data and isinstance(data, InstanceData) and data.bundle:
            data.bundle.addData(self)
        elif instance and isinstance(instance, Instance):
            instance.addData(self)
        elif data and isinstance(data, InstanceData) and data.instance:
            data.instance.addData(self)
        
        # some sanity checks (parameter missmatch might help detecting wrong configurations)
        if bundle and instance: assert bundle.instance == instance,         "bundle instacne and instance do not match"
        if data   and instance: assert data.instance   == instance,         "data instance and instance do not match"
        if data   and bundle:   assert data.instance   == bundle.instance,  "data and bundle instances do not match"

        # auto-increment path base name if it already exists
        if auto_increment and os.path.exists(self.abspath):
            self._increment_path()
                

    def _increment_path(self):
        # e.g. /path/to/file.txt -> /path/to/file_1.txt
        #      /path/to/file_1.txt -> /path/to/file_1_1.txt
        #      /path/to/file.txt -> /path/to/file_2.txt
        
        pbase = os.path.basename(self.dc.path)
        pfname, *pfext = pbase.split('.', maxsplit=1)
        
        i = 0
        while os.path.exists(self.abspath):
            i += 1

            new_path = pfname + '_' + str(i) 
            if len(pfext): new_path += '.' + pfext[0]
            self.dc.path = new_path

            if i > 100:
                raise Exception("Could not find a free path for data file")

    @property
    def instance(self) -> 'Instance':
        assert self._instance is not None
        return self._instance
    
    @instance.setter
    def instance(self, instance: 'Instance') -> None:
        self._instance = instance

        if self._bundle is None:
            self.dc.setParent(instance.dc)

    @property
    def bundle(self) -> Optional['InstanceDataBundle']:
        return self._bundle
    
    @bundle.setter
    def bundle(self, bundle: 'InstanceDataBundle') -> None:
        self._bundle = bundle
        self.dc.setParent(bundle.dc)

    @property
    def confirmed(self) -> bool:
        return self._confirmed
    
    def confirm(self) -> None:
        self._confirmed = True

    def getDataBundle(self, ref: str) -> 'InstanceDataBundle':
        return InstanceDataBundle(ref=ref, instance=self.instance, bundle=self.bundle)
    
    def __str__(self) -> str:
        srtd = "sorted" if isinstance(self.instance, SortedInstance) else "unsorted"
        return "<D:%s:%s:%s>"%(self.abspath, srtd, self.type)

from .Instance import Instance, SortedInstance
from .InstanceDataBundle import InstanceDataBundle
