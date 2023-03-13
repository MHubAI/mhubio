"""
-------------------------------------------------
MHub - Data bundle class for mhubio instances
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (27.02.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import Optional
from .DirectoryChain import DirectoryChainInterface

class InstanceDataBundle(DirectoryChainInterface):
    def __init__(self, ref: str, instance: 'Instance', bundle: Optional['InstanceDataBundle'] = None):
        self.instance: Instance = instance
        self._bundle: Optional[InstanceDataBundle] = bundle

        parent = self.instance if not self._bundle else self._bundle
        super().__init__(path=ref, base=None, parent=parent.dc)

    def __str__(self) -> str:
        s = f"<B:{self.abspath}"
        if self.dc.base: s+= f" (base: {self.dc.base})"
        if self.dc.isEntrypoint: s+= ":EP"
        s+= ">"
        return s

    def addData(self, data: 'InstanceData') -> None:
        self.instance.addData(data)
        data.bundle = self

from .InstanceData import InstanceData
from .Instance import Instance
