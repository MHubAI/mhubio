"""
-------------------------------------------------
MHub - Data handler class for the mhubio framework
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (27.02.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import List, Dict, Optional
from .DirectoryChain import DirectoryChainInterface, DirectoryChain
from .DataType import DataType
import uuid, os

class DataHandler(DirectoryChainInterface):
    # base:             str
    # _global_instance: Optional['Instance']
    # _instances:       List[Instance]
    # _tmpdirs:         Dict[str, str]

    def __init__(self, base: str) -> None:
        self._instances: List[Instance] = []
        self._tmpdirs: Dict[str, List[str]] = {}

        # setup directory chain
        super().__init__(path=base, base=None, parent=None)
        self.dc.makeEntrypoint()
        assert self.dc.isEntrypoint()
        
        # setup a global instance
        self._global_instance = Instance(path="_global")
        self._global_instance.attr["id"] = "global"
        self._global_instance.attr["sid"] = "global"
        self._global_instance.handler = self

    @property
    def globalInstance(self) -> 'Instance':
        return self._global_instance

    @property
    def instances(self) -> List['Instance']:
       return self._instances

    @instances.setter
    def instances(self, instances: List['Instance']) -> None:
        for instance in instances:
            instance.handler = self
        self._instances = instances

    def addInstance(self, instance: 'Instance') -> None:
        assert instance not in self._instances, "Error: instance already added to data handler."
        instance.handler = self
        self._instances.append(instance)

    def getInstances(self, sorted: bool, type: 'DataType') -> List['Instance']:
        i_type = SortedInstance if sorted else UnsortedInstance
        return [i for i in self.instances if isinstance(i, i_type) and i.hasType(type)]

    def requestTempDir(self, label: Optional[str] = None) -> str:
        abs_base = "/app/tmp"
        dir_name = str(uuid.uuid4())
        path  = os.path.join(abs_base, dir_name)

        # remember temporary abspath by label
        if label is None:
            # TODO: what about a garbage-collection like system for tmp dirs, allowing auto-release by label name? Otherwise, we can always just erase the entire /tmp stack. Only when disc space is an issue + a lot of files are generated (and never released) this should be considered. 
            print("WARNING: No label set for temporary dir.")
        else:
            if label not in self._tmpdirs:
                self._tmpdirs[label] = []
            self._tmpdirs[label].append(path)

        # make path
        os.makedirs(path)

        # return
        return path

    def export_yml(self, path: str) -> None:
        instances = []
        for instance in [self.globalInstance, *self.instances]:
            instance_dict = {
                'attr': instance.attr,
                'dc': {
                    'path': instance.dc.path,
                    'base': instance.dc.base
                },
                'files': []
            }
            for data in instance.data:
                files_dict = {
                    'path': data.dc.path,
                    'type': data.type.toString(),
                    'has_bundle': 'yes' if data.bundle else 'no',
                    'bundle': None,
                    'confirmed': data.confirmed,
                    'dc': data.dc.asDict()
                }

                if data.bundle:
                    files_dict['bundle'] = {
                        'path': data.bundle.abspath,
                        'dc': data.bundle.dc.asDict()
                    }

                instance_dict['files'].append(files_dict)
            instances.append(instance_dict)

        #
        import yaml
        with open(path, 'w') as f:
            yaml.dump(instances, f)

    def import_yml(self, path: str, check_files=True, confirm_files=False) -> None:
        from mhubio.core import Instance, InstanceData, DataType
        
        # read yml
        import yaml
        with open(path, 'r') as f:
            instances = yaml.load(f, Loader=yaml.FullLoader)

        # clean instances
        self.instances = []

        # create instances
        for instance in instances:

            # use global / create instance
            if instance['attr']['id'] != 'global':
                i = Instance(path=instance['dc']['path'])
                i.attr = instance['attr']
                self.addInstance(i)
            else:
                i = self.globalInstance

            # add data
            for files in instance['files']:

                # bundle
                b = None
                if files['bundle']:
                    b = InstanceDataBundle(files['bundle']['path'], instance=i)
                    b.dc = DirectoryChain.fromDict(files['bundle']['dc'])

                # data
                d = InstanceData(files['path'], DataType.fromString(files['type']), bundle=b, instance=i)
                
                # confirm
                if confirm_files:
                    if os.path.exists(d.abspath):
                        d.confirm()
                        
                elif files['confirmed']:

                    if check_files:
                        assert os.path.exists(d.abspath), f"Error: file {d.abspath} is confirmed but does not exist."

                    d.confirm()

    def printInstancesOverview(self, level: str = "data+meta"):
        assert level in ["data", "meta", "data+meta"]
        for instance in [self.globalInstance, *self.instances]:
            if level == "data":
                instance.printDataOverview(meta=False)
            elif level == "meta":
                instance.printDataMetaOverview()
            elif level == "data+meta":
                instance.printDataOverview(meta=True)


# avoiding circular imports
from .Instance import Instance, SortedInstance, UnsortedInstance
from .InstanceDataBundle import InstanceDataBundle