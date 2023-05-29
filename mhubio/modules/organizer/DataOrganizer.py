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
    set_file_permissions: bool 

    def __init__(self, config: Config, dry_run: bool = False, set_file_permissions: bool = False, **kwargs) -> None:
        super().__init__(config, **kwargs)
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
            [basename] -> basename of the datatype (os.path.basename(<DataType>.abspath))
            [filename] -> filename of the datatype (os.path.basename(<DataType>.abspath).split('.', 1)[0]))
            [filext] -> file extension of the datatype (os.path.basename(<DataType>.abspath).split('.', 1)[1]?)
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
                    elif var == "basename":
                        _target = _target.replace("[basename]", os.path.basename(data.abspath))
                    elif var == "filename":
                        _target = _target.replace("[filename]", os.path.basename(data.abspath).split('.', 1)[0])
                    elif var == "filext":
                        file_ext = os.path.basename(data.abspath).split('.', 1)[1] if '.' in os.path.basename(data.abspath) else ""
                        _target = _target.replace("[filext]", file_ext)
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

            self.v(f"> {type.toString()} -> {target}")
            
            if not instance.hasType(type):
                self.v(f"type {str(type)} not in instance. all types are:")
                for d in instance.data:
                    self.v("> ", str(d.type), d.abspath)
                continue

            # get input file path
            inp_datas = instance.data.filter(type, confirmed_only=self.getConfiguration("require_data_confirmation", True))
            for inp_data in inp_datas:

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
                    # copy directory or file
                    if os.path.isdir(inp_data.abspath):
                        shutil.copytree(inp_data.abspath, out_data.abspath)
                    elif os.path.isfile(inp_data.abspath):
                        shutil.copyfile(inp_data.abspath, out_data.abspath)
                    else:
                        raise FileNotFoundError(f"Could not copy {inp_data.abspath} to {out_data.abspath}. File not found.")
                    
                    # set permissions to 777 (iteratively for directories)
                    if self.set_file_permissions: 
                        if os.path.isfile(out_data.abspath):
                            os.chmod(out_data.abspath, 0o777)
                        elif os.path.isdir(out_data.abspath):
                            for dirpath, _, filenames in os.walk(out_data.abspath):
                                os.chmod(dirpath, 0o777)
                                for filename in filenames:
                                    os.chmod(os.path.join(dirpath, filename), 0o777)

                else:
                    print(f"dry copy {inp_data.abspath} to {out_data.abspath}")

                
