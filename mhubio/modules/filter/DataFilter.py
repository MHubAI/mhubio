"""
-------------------------------------------------
MHub - Instance Filter Base Module.
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import List
from mhubio.core import Module, Instance, DataType, FileType

class DataFilter(Module):
    """
    Filter Module.
    Base implementation for filter operations.
    DEVNOTE: To simplify filter subclasses, a list of instances is passed to the generic filter function, making subclasses independand from the internally-global config and data handler instances.
    """
    
    def task(self) -> None:
        self.config.data.instances = self.filter(self.config.data.instances)

    def filter(self, instances: List[Instance]) -> List[Instance]:
        return instances

class TypeFilter(DataFilter):
    type: DataType

    def filter(self, instances: List[Instance]):
        return [i for i in instances if i.hasType(self.type)]

class AttributeFilter(DataFilter):
    def filterFor(self, key: str, value: str) -> None:
        self._filter_attr_key = key
        self._filter_attr_val = value

    def filter(self, instances: List[Instance]) -> List[Instance]:
        return [i for i in instances if self._filter_attr_key in i.attr and i.attr[self._filter_attr_key] == self._filter_attr_val]

class SIDFilter(DataFilter):
    """
    For dev speedup only.
    """
    sid: str

    def getInstanceSid(self, instance: Instance) -> str:
        dicom_data = instance.data.filter(DataType(FileType.DICOM)).first()
        sid = dicom_data.abspath.split("/")[-2]
        print("ABS DICOM PATH: ", dicom_data.abspath, " | SID: ", sid)
        return sid

    def filter(self, instances: List[Instance]):
        return [i for i in instances if self.getInstanceSid(i) == self.sid]
