"""
-------------------------------------------------
MHub - Module to remove files not needed for 
       processing. Removes files either by a 
       matching DTQ or by a exclusion DTQ.
       NOTE: prefix the  query with NOT to invert
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
Date:   15.04.2024
-------------------------------------------------
"""

from mhubio.core import Module, Instance, IO, DataTypeQuery

@IO.Config('query', DataTypeQuery, '', factory=DataTypeQuery, the='DTQ to match all files to remove')
class FileRemover(Module):

    query: DataTypeQuery

    @IO.Instance()
    def task(self, instance: Instance) -> None:

        # filter data by query
        datas = instance.data.filter(self.query, confirmed_only=False)
        
        # print the list of files that will be removed
        self.log("Removing the following files:")
        self.log(" query: ", self.query)
        for data in datas:
            self.log("- ", data.abspath)
        
        # remove data and unlink from instance
        instance.data.remove(datas, delete_files=True)