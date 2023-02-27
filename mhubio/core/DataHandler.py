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
from .DirectoryChain import DirectoryChainInterface
from .DataType import DataType
import uuid, os

class DataHandler(DirectoryChainInterface):
    # base:         str
    # _instances:   List[Instance]
    # _tmpdirs:     Dict[str, str]

    def __init__(self, base: str) -> None:
        self._instances: List[Instance] = []
        self._tmpdirs: Dict[str, List[str]] = {}

        super().__init__(path=base, base=None, parent=None)
        self.dc.makeEntrypoint()
        assert self.dc.isEntrypoint()

    @property
    def instances(self) -> List['Instance']:
       return self._instances

    @instances.setter
    def instances(self, instances: List['Instance']) -> None:
        for instance in instances:
            instance.handler = self
        self._instances = instances

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

    def printInstancesOverview(self, level: str = "data+meta"):
        assert level in ["data", "meta", "data+meta"]
        for instance in self.instances:
            if level == "data":
                instance.printDataOverview(meta=False)
            elif level == "meta":
                instance.printDataMetaOverview()
            elif level == "data+meta":
                instance.printDataOverview(meta=True)


# avoiding circular imports
from .Instance import Instance, SortedInstance, UnsortedInstance