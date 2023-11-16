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

@IO.Config('requires', list, [], the="list of datatype queries for which only instances that contain a matching file will be kept.")
class FileFilter(InstanceFilter):

    requires: list

    def explain_criteria(self): 
        self.log("This filter will exclude all instances not containing at least one file for each of the following datatype queries")
        for dtq in self.requires: 
            self.log("-", dtq)

    def filter(self, instances: List[Instance]) -> List[Instance]:
        matching_instances = []
        for instance in instances:
            isMatching = True
            
            for dtq in self.requires:
                #print("filtering instance", instance, "for", dtq)
                #c = instance.data.filter(dtq)
                #print("filter result", [str(f) for f in c]) 
                if len(instance.data.filter(dtq)) == 0:
                    isMatching = False
                    break

            if isMatching:
                matching_instances.append(instance)
                    
        return matching_instances