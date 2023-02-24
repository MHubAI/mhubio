"""
-------------------------------------------------
MHub - Config, Instance & Data Classes
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""


import os, time, uuid, yaml
from enum import Enum
from typing import List, Dict, Union, Optional, Tuple, Type, Any

def dict_merge(source: dict, destination: dict) -> dict:
    for k, v in source.items():
        if isinstance(v, dict):
            n = destination.setdefault(k, {})
            dict_merge(v, n)
        else:
            destination[k] = v
    return destination


class FileType(Enum):
    NONE = None
    NRRD = "nrrd"
    NIFTI = "nifti"
    DICOM = "dicom"
    DICOMSEG = "dicomseg"
    RTSTRUCT = "RTSTRUCT"

    def __str__(self) -> str:
        return self.name
    

class DirectoryChain:
    """Directory chain (DC) is a recursive data structure that represents a path chain. 
    DC helps implementing a hierarchical data structure by mapping folder structure to semantic context.
    Given a hierarchical chain like A > B > C > D. If data is added to C, A/B/C is considered the context.
    
    Each DC instance has a path set at instantiation. 
    The instance's absolute path following the hiorarchical structure is provided by the abspath property.

    Although the hierarchical structure should be maintained whenever feasable, it is possible to set an absoluter path at any point in the hierarchical chain, making the instance a so called entrypoint. This can be achieved by one of the folowing options: 
    - set an absolut path (starting with /) as the DC instance's path
    - set the instance's base (path will be prefixed with base set base to an empty string to use path directly) 
    - call the instance's `makeEntrypoint(enforceAbsolutePath: bool = True)` method. 

    If an instance is an entrypoint can be checked by calling the `isEntrypoint()` method.
    """

    # path: str
    # base: str 
    # abspath: str

    def __init__(self, path: str, base: Optional[str] = None, parent: Optional['DirectoryChain'] = None) -> None:
        self.path: str = path
        self.base: Optional[str] = base
        self.parent: Optional[DirectoryChain] = parent

    def setBase(self, base: Optional[str]) -> None:
        self.base = base

    def setParent(self, parent: Optional['DirectoryChain']) -> None:
        self.parent = parent

    def setPath(self, path: str) -> None:
        self.path = path

    def isEntrypoint(self) -> bool:
        return self.base is not None or self.path[:1] == os.sep

    def makeEntrypoint(self, enforceAbsolutePath: bool = True) -> None:
        if enforceAbsolutePath:
            self.setBase("/")
        else:
            self.setBase("")

    @property
    def abspath(self) -> str:
        if self.base is not None:
            return os.path.join(self.base, self.path)
        elif self.parent is not None:
            return os.path.join(self.parent.abspath, self.path)
        else:
            return self.path


class DirectoryChainInterface:
    """Every class part of a hierarchical data structure dealing with representative data should inherit from this class.
    By inheriting from this class, the class will have a `dc` property that is an instance of DirectoryChain and an `abspath` property that is a shortcut `self.dc.abspath`.
    """

    def __init__(self, path: str, base: Optional[str] = None, parent: Optional['DirectoryChain'] = None) -> None:
        self.dc = DirectoryChain(path, base, parent)

    @property
    def abspath(self) -> str:
        return self.dc.abspath


class Meta:

    def __init__(self, key: Optional[str] = None, value: Optional[str] = None) -> None:
        self.mdict: Dict[str, str] = {key: value} if key and value else {}

    def ext(self, meta: Union[Dict[str, str], List['Meta'], 'Meta']) -> 'Meta':
        if isinstance(meta, dict):
            self.mdict = {**self.mdict, **meta}
        elif isinstance(meta, list) and all([isinstance(m, Meta) for m in meta]):
            for m in meta:
                self.mdict = {**self.mdict, **m.mdict}
        elif isinstance(meta, Meta):
            self.mdict = {**self.mdict, **meta.mdict}
        else:
            raise ValueError("Malformed metadata passed to DataType.")
        return self

    def keys(self) -> List[str]:
        return list(self.mdict.keys())

    def items(self) -> List[Tuple[str, str]]:
        return [(k, v) for k, v in self.mdict.items()]

    # +
    def __add__(self, o: Union[Dict[str, str], List['Meta'], 'Meta']) -> 'Meta':
        return Meta().ext(self).ext(o)

    # -
    def __sub__(self, rks: List[str]) -> 'Meta':
        assert isinstance(rks, list) and all([isinstance(k, str) for k in rks])
        return Meta().ext({k: v for k, v in self.items() if not k in rks})

    # =
    def __eq__(self, o: Union[Dict[str, str], 'Meta']) -> bool:
        return self.mdict == (o.mdict if isinstance(o, Meta) else o)

    # in
    def __contains__(self, ks: Union[str, List[str]]) -> bool:
        assert isinstance(ks, str) or isinstance(ks, list) and all([isinstance(k, str) for k in ks])
        return ks in self.mdict if isinstance(ks, str) else all([k in self.mdict for k in ks])

    # <=
    # "less" is defined as "less general" (or more specific) since it targets a smaller subset of all possible combinations
    def __le__(self, o: Union[Dict[str, str], 'Meta']) -> bool:
        omdict = (o.mdict if isinstance(o, Meta) else o)
        assert isinstance(omdict, dict)
        for k, v in omdict.items():
            if self[k] != v:
                return False
        return True

    # []
    def __getitem__(self, key: str) -> str:
        assert isinstance(key, str)
        return self.mdict[key] if key in self.mdict else ""

    def __str__(self) -> str:
        return ":".join(["%s=%s"%(k, v) for k, v in self.mdict.items()])

    def __len__(self) -> int:
        return len(self.mdict)

    def __bool__(self) -> bool:
        return len(self) > 0


# define common types
CT      = Meta("mod", "ct")
CBCT    = Meta("mod", "cbct")
MRI     = Meta("mod", "mri")
XRAY    = Meta("mod", "xray")
SEG     = Meta("mod", "seg")


class DataType:
    def __init__(self, ftype: FileType, meta: Optional[Meta] = None) -> None:
        self.ftype: FileType = ftype
        self.meta: Meta = meta if meta else Meta()

    def __str__(self) -> str:
        s: str = "[T:" + str(self.ftype)
        if self.meta: s += ":" + str(self.meta)
        s += "]"
        return s


class Instance(DirectoryChainInterface): 
    # handler:      DataHandler
    # path:         str
    # _data:        List[InstanceData]
    # attr:         Dict[str, str]

    def __init__(self, path: str = "") -> None:
        super().__init__(path=path, parent=None, base=None)
        self._handler: Optional['DataHandler'] = None            # NOTE: handler is set delayed but is NOT OPTIONAL !
        self._data: List['InstanceData'] = []
        self.attr: Dict[str, str] = {'id': str(uuid.uuid4())}

    @property
    def handler(self) -> 'DataHandler':
        assert self._handler is not None
        return self._handler
    
    @handler.setter
    def handler(self, handler: 'DataHandler'):
        self._handler = handler
        self.dc.setParent(handler.dc)

    @property
    def data(self) -> List['InstanceData']:
        return self._data

    @data.setter
    def data(self, data: List['InstanceData']):
        for d in data:
            d.instance = self
        self._data = data

    def hasType(self, type: DataType) -> bool:
        return len([d for d in self.data if d.type.ftype == type.ftype]) > 0 # FIXME: need proper matching!!! 

    def getDataMetaKeys(self) -> List[str]:
        return list(set(sum([list(d.type.meta.keys()) for d in self.data], [])))

    def printDataOverview(self, datas: Optional[List['InstanceData']] = None, meta: bool = False, label: str = "") -> None:

        # you may specify data explicitly (e.g. the result of a filter), otherwise we use the instance's data
        if datas is None:
            datas = self.data

        # formatting options
        # TODO: outsource or standardize if used frequently
        chead = '\033[95m'
        cyan = '\033[96m'
        cend = '\033[0m'
        fitalics = '\x1B[3m'
        fnormal ='\x1B[0m'

        # print fromatted output
        print(f". {fitalics}{label}{fnormal} [{self.abspath}]")
        for data in datas:
            print(f"├── {chead}{str(data.type.ftype)}{cend} [{data.abspath}]")

            # print meta    
            if meta:
                for k, v in data.type.meta.items():
                    print(f"│   ├── {cyan}{k}: {v}{cend}")

    def printDataMetaOverview(self, datas: Optional[List['InstanceData']] = None, compress: bool = True, label: str = "") -> None:

        # you may specify data explicitly (e.g. the result of a filter), otherwise we use the instance's data
        if datas is None:
            datas = self.data
               
        # count
        cnt: Dict[FileType, Dict[str, Dict[str, int]]] = {}
        cnt_ftype: Dict[FileType, int] = {}

        for data in datas:

            # count filetypes (regardless of meta presence)
            if not data.type.ftype in cnt_ftype: cnt_ftype[data.type.ftype] = 0
            cnt_ftype[data.type.ftype] += 1

            # count meta 
            for k, v in data.type.meta.items():
                if not data.type.ftype in cnt: cnt[data.type.ftype] = {}
                if not k in cnt[data.type.ftype]: cnt[data.type.ftype][k] = {}
                if not v in cnt[data.type.ftype][k]: cnt[data.type.ftype][k][v] = 0

                cnt[data.type.ftype][k][v] += 1

        # formatting options
        # TODO: outsource or standardize if used frequently
        chead = '\033[95m'
        cyan = '\033[96m'
        cend = '\033[0m'
        fitalics = '\x1B[3m'
        fnormal ='\x1B[0m'

        # get maximal terminal length or set a default length
        try:
            maxTerminalLength = os.get_terminal_size().columns
        except OSError as e:
            maxTerminalLength = 100

        # print fromatted output
        print(f". {fitalics}{label}{fnormal}")
        for ftype in cnt_ftype:
            print(f"├── {chead}{str(ftype)}{cend} [{cnt_ftype[ftype]}]")
            if not ftype in cnt: continue
            for k in cnt[ftype]:
                print(f"|   ├── {cyan}{k:<20}{cend}")
                for v, n in cnt[ftype][k].items():
                    if not compress or n > 1:
                        print(f"|   |   ├── ({n:<4}) {cyan}{v}{cend}")
                if compress:
                    n1lst = sorted([v for v, n in cnt[ftype][k].items() if n == 1])

                    if n1lst:
                        print(f"|   |   ├── ", end="")
                        
                        while n1lst:
                            cc = 12
                            while n1lst and cc + len(str(n1lst[0])) + 2 < maxTerminalLength:
                                print(str(n1lst[0]) + ", ", end="")
                                cc  += len(str(n1lst[0])) + 2
                                n1lst = n1lst[1:]
                            if n1lst:
                                print(f"\n|   |   |   ", end="")
                        print("")

    def filterData(self, ref_types: Union[DataType, List[DataType]]) -> List['InstanceData']:
        if not isinstance(ref_types, list):
            ref_types = [ref_types]
        return list(set(sum([self._filterData(ref_type) for ref_type in ref_types], [])))       

    def _filterData(self, ref_type: DataType) -> List['InstanceData']: 
        """
        Filter for instance data by a reference data type. Only instance data that match the file type and specified meta data of the reference type are returned. A datatype matches the reference type, if all metadata of the reference type is equal to the datatype. If a datatype contains additional meta data compared to the reference type (specialization) those additional keys are ignored. 
        """

        # collect only instance data passing all checks (ftype, meta)
        matching_data: List[InstanceData] = []

        # iterate all instance data of this instance
        for data in self.data:
            # check file type, ignore other filetypes
            if not data.type.ftype == ref_type.ftype:
                continue

            # check if metadata is less general than ref_type's metadata
            if not data.type.meta <= ref_type.meta:
                continue
          
            # add instance data that passes all prior checks
            matching_data.append(data)

        # return matches
        return matching_data

    def getData(self, ref_types: DataType) -> 'InstanceData':
        fdata = self.filterData(ref_types)

        # warning if multiple data available
        if len(fdata) > 1: 
            print("Warning, type is not unique. First element is returned.")
        
        #FIXME: when adding exception management, this should throw
        if len(fdata) == 0: 
            print("Ooops, no data found.")
            print("> You were asking for " + str(ref_types) + ". But all I have is:")
            print("> ", "\n> ".join([str(x) for x in self.data]))

        # return data
        return fdata[0]

    # TODO: make it possible to connect data and instance such that all paths are calculatedd correctly but the data is "invisible" to the instance (at salvo). Invoke a .complete() method to resolve. Technically, this can already be achived (although not as obvious to the reader) by first assigning th einstance to the data (data.instance = instance) but without adding th edata to the instance (which has to be done later a.k.a. resolving). We could, however, check if data has a diverging instance and in that case forbid adding (assert data.instance is None or self)
    # e.g. add , salvo: bool = False to addData signature
    def addData(self, data: 'InstanceData') -> None:
        data.instance = self
        self._data.append(data)

    def __str__(self) -> str:
        return "<I:%s>"%(self.abspath)
    
    def getDataBundle(self, ref: str) -> 'InstanceDataBundle':
        return InstanceDataBundle(ref=ref, instance=self)


class InstanceDataBundle(DirectoryChainInterface):
    def __init__(self, ref: str, instance: Instance, bundle: Optional['InstanceDataBundle'] = None):
        self.instance: Instance = instance
        self._bundle: Optional[InstanceDataBundle] = bundle

        parent = self.instance if not self._bundle else self._bundle
        super().__init__(path=ref, base=None, parent=parent.dc)

    def addData(self, data: 'InstanceData') -> None:
        self.instance.addData(data)
        data.bundle = self


class InstanceData(DirectoryChainInterface):
    # instance:     Instance
    # type:         DataType
    # path:         str
    # base:         str
    
    def __init__(self, path: str, type: DataType) -> None:
        self._instance: Optional[Instance] = None
        self._bundle: Optional[InstanceDataBundle] = None
        self.type: DataType = type
        super().__init__(path=path, base=None, parent=None)

    @property
    def instance(self) -> Instance:
        assert self._instance is not None
        return self._instance
    
    @instance.setter
    def instance(self, instance: Instance) -> None:
        self._instance = instance

        if self._bundle is None:
            self.dc.setParent(instance.dc)

    @property
    def bundle(self) -> Optional[InstanceDataBundle]:
        return self._bundle
    
    @bundle.setter
    def bundle(self, bundle: InstanceDataBundle) -> None:
        self._bundle = bundle
        self.dc.setParent(bundle.dc)

    def getDataBundle(self, ref: str) -> InstanceDataBundle:
        return InstanceDataBundle(ref=ref, instance=self.instance, bundle=self.bundle)
    
    def __str__(self) -> str:
        srtd = "sorted" if isinstance(self.instance, SortedInstance) else "unsorted"
        return "<D:%s:%s:%s>"%(self.abspath, srtd, self.type)


class UnsortedInstance(Instance):
    def __init__(self, path: str = "") -> None:
        super().__init__(path)


class SortedInstance(Instance):
    def __init__(self, path: str = "") -> None:
        super().__init__(path)


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
    def instances(self) -> List[Instance]:
       return self._instances

    @instances.setter
    def instances(self, instances: List[Instance]) -> None:
        for instance in instances:
            instance.handler = self
        self._instances = instances

    def getInstances(self, sorted: bool, type: DataType) -> List[Instance]:
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

class Config:
    # data: DataHandler

    # TODO: config will load it's dynamic, configurable attributes from yaml or json file. 
    # The config should be structured such that there is a shared config accessiblae to all modules and a (optional) config for each Module class. Class inheritance is followed naturally.

    def __init__(self, config_file: Optional[str] = None, config: Optional[dict] = None) -> None:
        self.verbose = True
        self.debug = False

        # TODO: define minimal base config and auto-load. 
        # How do we 'define' mandatory fields? assert them?
        if config_file is not None and os.path.isfile(config_file):
            with open(config_file, 'r') as f:
                self._config = yaml.safe_load(f)
        elif config_file is not None:
            print(f"WARNING: config file {config_file} not found.")
        else:
            # TODO: define & load base config
            print(f"WARNING: base config loaded.")
            self._config = {
                'general': {
                    'data_base_dir': '/data'
                },
                'modules': {}
            }

        # override / extend file based config with explicit configurations (if any)
        if config is not None:
            print("Updating config with explicit settings.")
            print(self._config)
            print(config)
            self._config = dict_merge(config, self._config.copy())
            print(self._config)

        # Create a data handler with no instances.
        # NOTE: The first module should always be an importer module importing instances and instance data.
        self.data = DataHandler(base=self['data_base_dir'])

    def __getitem__(self, key: Union[str, Type['Module']]) -> Any:
        if isinstance(key, str) and key in self._config['general']:
            return self._config['general'][key]
        elif isinstance(key, type) and key.__name__ in self._config['modules']:
            return self._config['modules'][key.__name__]
        else:
            print(f"WARNING: config '{key}' not defined.") 
            print(self._config['modules'])

    # TODO: check mode on all! os.makedirs operations (os.makedirs(name=d, mode=0o777))
        

class Module:
    # label:    str
    # config:   Config
    # verbose:  bool
    # debug:    bool

    def __init__(self, config: Config) -> None:
        self.label: str = self.__class__.__name__
        self.config: Config = config
        self.verbose: bool = config.verbose
        self.debug: bool = config.debug

    @property 
    def c(self) -> Any:
        return self.config[self.__class__]

    def v(self, *args) -> None:
        if self.verbose:
            print(*args)

    def execute(self) -> None:
        self.v("\n--------------------------")
        self.v("Start %s"%self.label)
        start_time = time.time()
        self.task()
        elapsed = time.time() - start_time
        self.v("Done in %g seconds."%elapsed)

        if self.debug:
            self.v("\n-debug--------------------")
            self.config.data.printInstancesOverview()

    def task(self) -> None:
        """
        The task to execute on the module.
        This method needs to be overwriten in all module implementations.
        """
        print("Ooops, no task implemented in base module.")
        pass


class Sequence(Module):
    """
    Sequentially execute a sequence of Module instances.
    """

    def __init__(self, config: Config, modules: List[Type[Module]]) -> None:
        super().__init__(config)
        self.modules = modules

    def task(self) -> None:
        for module in self.modules:
            module(self.config).execute()