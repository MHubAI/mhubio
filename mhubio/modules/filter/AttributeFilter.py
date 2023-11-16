"""
-------------------------------------------------
MHub - Attribute Instance Filter Module.
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import List
from mhubio.modules.filter.InstanceFilter import InstanceFilter
from mhubio.core import Instance, IO

@IO.Config("instance_attributes", dict, {}, the="instance attributes to filter for")
class AttributeFilter(InstanceFilter):

    instance_attributes: dict

    def explain_criteria(self):
        self.log("This filter will exclude all instances that do not have at least one attribute matching any of the following criteria:")
        for k, v in self.instance_attributes: 
            self.log("-", k, "=", v)

    def filter(self, instances: List[Instance]) -> List[Instance]:
        matching_instances = []
        for instance in instances:
            for k, v in self.instance_attributes.items():
                if k in instance.attr and ( 
                       (isinstance(v, list) and instance.attr[k] in v)  
                    or (isinstance(v, int)  and instance.attr[k] == v) 
                    or (isinstance(v, str)  and (v == "*" or instance.attr[k].lower() == v.lower())) 
                ):
                    matching_instances.append(instance)
        return matching_instances