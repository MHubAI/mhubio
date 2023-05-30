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
from mhubio.modules.filter.DataFilter import DataFilter
from mhubio.core import Instance, IO

@IO.Config("instance_attributes", dict, {}, the="instance attributes to filter for")
class AttributeFilter(DataFilter):

    instance_attributes: dict

    def filter(self, instances: List[Instance]) -> List[Instance]:
        matching_instances = []
        for instance in instances:
            for k, v in self.instance_attributes.items():
                if k in instance.attr and (v == '*' or instance.attr[k].lower() == v.lower()):
                    matching_instances.append(instance)
        return matching_instances