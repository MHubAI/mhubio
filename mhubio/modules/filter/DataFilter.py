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
from mhubio.core import Module, Instance, DataType, FileType, IO

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