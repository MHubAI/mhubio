"""
-------------------------------------------------
MHub - Instance data class for mhubio framework
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (27.02.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import Optional
from .DirectoryChain import DirectoryChainInterface
from .DataType import DataType

class InstanceData(DirectoryChainInterface):
    # instance:     Instance
    # type:         DataType
    # path:         str
    # base:         str
    
    def __init__(self, path: str, type: DataType, instance: Optional['Instance'] = None) -> None:
        super().__init__(path=path, base=None, parent=None)
        self._instance: Optional[Instance] = None
        self._bundle: Optional[InstanceDataBundle] = None
        self.type: DataType = type

        if instance is not None and isinstance(instance, Instance):
            #self.instance = instance    # A: d-->i link only 
            instance.addData(self)       # B: d<->i dual link 

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

    def getDataBundle(self, ref: str) -> 'InstanceDataBundle':
        return InstanceDataBundle(ref=ref, instance=self.instance, bundle=self.bundle)
    
    def __str__(self) -> str:
        srtd = "sorted" if isinstance(self.instance, SortedInstance) else "unsorted"
        return "<D:%s:%s:%s>"%(self.abspath, srtd, self.type)

from .Instance import Instance, SortedInstance
from .InstanceDataBundle import InstanceDataBundle
