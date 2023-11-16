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
from mhubio.core import Module, Instance

class InstanceFilter(Module):
    """
    Filter Module.
    Base implementation for filter operations.
    DEVNOTE: To simplify filter subclasses, a list of instances is passed to the generic filter function, making subclasses independand from the internally-global config and data handler instances.
    """
    
    def task(self) -> None:

        # get instances
        available_instances = self.config.data.instances

        # logging
        self.log("Filtering instances with", self.__class__.__name__)
        self.explain_criteria()

        # execute filter
        filtered_instances = self.filter(available_instances)

        # logging
        self.log("Available instances:", len(available_instances))
        self.log("Remaining instances:", len(filtered_instances))
        self.log("Excluded the following instances:")
        for i in available_instances:
            if i not in filtered_instances:
                self.log(" -", i)

        # update data handler
        self.config.data.instances = filtered_instances

    def explain_criteria(self):
        pass

    def filter(self, instances: List[Instance]) -> List[Instance]:
        return instances
