"""
-------------------------------------------------
MHub - Data Organizer Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import Dict, Optional
import os, shutil, uuid, re
from mhubio.core import Config, Module, Instance, InstanceData, DataType, FileType, Meta


class DataOrganizer(Module):
    target: Dict[DataType, str] = {}

    def __init__(self, config: Config, dry_run: bool = False, set_file_permissions: bool = False) -> None:
        super().__init__(config)
        self.dry = dry_run
        self.set_file_permissions = set_file_permissions

        # import targets from config if defined
        self._importTargetsFromConfig()

    def _importTargetsFromConfig(self) -> None:
        """
        conversion example [code implementation / config dictionary]  
        restricted characters: [':', '=', '-->']

        organizer.setTarget(DataType(FileType.NIFTI, CT), "/app/data/output_data/[i:SeriesID]/[path]")
        organizer.setTarget(DataType(FileType.DICOMSEG, SEG), "/app/data/output_data/[i:SeriesID]/TotalSegmentator.seg.dcm")

        {
          "modules": {
              "DataOrganizer": {
                  "targets": [
                      "NIFTI:mod=ct-->/app/data/output_data/[i:SeriesID]/[path]",   
                      "DICOMSEG:mod=seg-->/app/data/output_data/[i:SeriesID]/TotalSegmentator.seg.dcm"
                  ]
             }
        }
        """

        # automatically import targets from config if defined
        targets = self.getConfiguration("targets")
        if targets and isinstance(targets, list):
            for target_definition in self.c["targets"]:
                try:
                    assert isinstance(target_definition, str), f"Definition must be a string, not {type(target_definition)}."
                    
                    # extract source and target
                    src_def, tar_def = target_definition.split("-->")

                    # create data type instance
                    data_type = DataType.fromString(src_def)

                    # set target 
                    self.setTarget(data_type, tar_def)
                except Exception as e:
                    print(f"WARNING: could not parse target definition '{target_definition}: {str(e)}'")

    def setTarget(self, type: DataType, dir: str) -> None: # TODO: define copy / move action
        """
        Target directory where files of matching data type are copied to.
        Absolute path required. 
        Dynamic options:
            [random] -> random uuid4 string
            [path] -> relative path of the datatype (<DataType>.path)
            [i:id] -> instance id
            [i:...] -> any attribute from instance id (<Instance>.attr[...])
            [d:...] -> any metadata from datatype (<DataType>.meta[...])
        """
        self.target[type] = dir

    def task(self) -> None:
        for instance in self.config.data.instances:
            self.organize(instance)

    def resolveTarget(self, target: str, data: InstanceData) -> Optional[str]:
        vars = re.findall(r"\[(i:|d:)?([\w\_\-]+)\]", target)

        if len(vars) == 0:
            return target
        else:
            _target = target
            for scope, var in vars:
                if scope == "":
                    if var == "random":
                        _target = _target.replace('[random]', str(uuid.uuid4()))
                    elif var == "path":
                        _target = _target.replace("[path]", data.dc.path)
                elif scope == "i:" and data.instance is not None:
                    if not var in data.instance.attr:
                        print(f"WARNING: attribute '{var}' missing in instance {data.instance}. Case ignored.")
                        return None
                    _target = _target.replace('[' + scope + var + ']', data.instance.attr[var])
                elif scope == "d:":
                    if not var in data.type.meta:
                        print(f"WARNING: key '{var}' missing in datatype {data.type}. Case ignored.")
                        return None
                    _target = _target.replace('[' + scope + var + ']', data.type.meta[var])
                else:
                    raise ValueError(f"Unresolved pattern: '{scope}:{var}' in {target}.")

            return _target

    def organize(self, instance: Instance) -> None:
        
        self.v("organizing instance", str(instance))
        
        for (type, target) in self.target.items():
            
            if not instance.hasType(type):
                self.v(f"type {str(type)} not in instance. all types are:")
                for d in instance.data:
                    self.v("> ", str(d.type), d.abspath)
                continue

            # get input file path
            inp_datas = instance.filterData(type)
            for inp_data in inp_datas:

                # accept only confirmed data
                if not inp_data.confirmed:
                    continue

                inp_data_target = self.resolveTarget(target, inp_data)
                if not inp_data_target:
                    continue                

                # create target directory if required
                inp_data_target_dir = os.path.dirname(inp_data_target)
                if not self.dry and not os.path.isdir(inp_data_target_dir):
                    os.makedirs(inp_data_target_dir)
                    if self.set_file_permissions: os.chmod(inp_data_target_dir, 0o777)
                    self.v(f"created directory {inp_data_target_dir}")

                # add to instance
                # TODO: the data is now outside of our managed file structure but should still be linked to the instance. For now, just set the base path. However, this will cause type duplications thus not yet compatible with conversion modules applied afterwards. However, we've to decide if we enforce all conversion steps to only operate on our internal data structure.
                out_data = InstanceData(inp_data_target, type)
                out_data.dc.makeEntrypoint()
                instance.addData(out_data) # TODO: either remove dry mode or handle 

                # copy
                if not self.dry:
                    shutil.copyfile(inp_data.abspath, out_data.abspath)
                    if self.set_file_permissions: os.chmod(out_data.abspath, 0o777)
                else:
                    print(f"dry copy {inp_data.abspath} to {out_data.abspath}")

                
