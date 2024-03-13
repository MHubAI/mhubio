"""
---------------------------------------------------------
MHub - File Importer Module

Import files from the input directory (or a specified 
directory) into existing instances.
---------------------------------------------------------
Author: Leonard Nürnberg
Email:  lnuernberg@bwh.harvard.edu
Date:   07.03.2024
---------------------------------------------------------
"""

import os
from typing import Optional
from mhubio.core import Instance, InstanceData, DataType, IO, Module, Meta

@IO.Config("input_dir", str, "input_data", the="input directory to import files from.")
@IO.Config("deep", bool, False, the="whether to search for files in subdirectories.")
@IO.Config("instance_id", str, "sid", the="instance attribute to match the imported files to.")
@IO.Config("type", str, "", the="file type (file extension) to import.")
@IO.Config("meta", Meta, "", factory=Meta.fromString, the="static metadata added to any file imported by the file importer.")
class FileImporter(Module):
  
    input_dir: str
    deep: bool
    instance_id: str
    meta: Meta
    type: str
    
    def _getInstanceById(self, instance_id: str) -> Optional[Instance]:
        for instance in self.config.data.instances:
            if instance.attr[self.instance_id] == instance_id:
                return instance
    
    def conditionally_import_file(self, file_path: str) -> None:
        
        # extract file name (without extension) and file extension
        file_name = os.path.basename(file_path)
        file_name_no_ext, file_ext = os.path.splitext(file_name)
        
        # check extension if specified (allow all extensions when empty)
        if len(self.type) and file_ext[1:] not in self.type.split("|"):
            return
        
        # find matching file type based on extension 
        #  NOTE: file_ext starts with a dot (e.g., '.json')
        try: 
            file_type = DataType.fromString(file_ext[1:])
            file_type.meta = self.meta
        except:
            return 
        
        # get instance
        instance = self._getInstanceById(file_name_no_ext)
        
        if not instance:
            return
        
        # create data and add it to the instance
        data = InstanceData(path=file_path, type=file_type, instance=instance)
        
        # TODO: eventually copy data to instance directory
        # ...
        
        # confirm the data
        data.confirm()

    def task(self) -> None:
        
        # get input directory
        input_dir = os.path.join(self.config.data.abspath, self.input_dir)
        
        # walk through the entire input directory
        if not self.deep:
            for file in os.listdir(input_dir):
                self.conditionally_import_file(os.path.join(input_dir, file))
        else:
            for root, _, files in os.walk(input_dir):
                for file in files:
                    self.conditionally_import_file(os.path.join(root, file))