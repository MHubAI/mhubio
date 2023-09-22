"""
-------------------------------------------------
MHub - FileStructureImporter 
This module imports data highly dynamic and 
customizable from the input directory 
structure. Import rules are defined in the 
configuration file.
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg 
Email:  leonard.nuernberg@maastrichtuniversity.nl
Date:   28.02.2022
-------------------------------------------------
"""

from typing import List, Dict, Optional 
from typing_extensions import TypedDict, NotRequired
from mhubio.core import Module, Instance, InstanceData, InstanceDataBundle, DataType, IO
from mhubio.core.Logger import ConsoleCapture
import os, csv, copy, uuid, re, shutil

class ScanFeature(TypedDict):
    path: str
    meta: Dict[str, str]
    dtype: str
    bundle: NotRequired[str]

@IO.Config('input_dir', str, 'input_data', the='The input directory that is scanned for data.')
@IO.Config('instance_dir', str, 'imported_instances', the='The directory where instances are stored.')
@IO.Config('structures', List[str], [], the='The directory structure that is used to parse meta data from the input directory.')
@IO.Config('excludes', List[str], [], the='directory structure that is used to exclude directories from the input directory.')
@IO.Config('meta', List[Dict[str, str]], [], the='meta data lookup definition')
@IO.Config('import_id', str, '_instance', the='meta key pattern, that is used to reference/identify instances.')
@IO.Config('outsource_instances', bool, True, the='flag if set, instances are always outsourced to the instance directory.')
class FileStructureImporter(Module):
    """
    Structural Importer Module.
    Import data from a input directory structure.

    configuration:
        input_dir: str  (default: 'input_data')
            The input directory that is scanned for data.
        instance_dir: str (default: 'imported_instances')
            The directory where instances are stored.
        structures: List[str] (default: []) 
            The directory structure that is used to parse meta data from the input directory.
            The structure is defined as a list of strings. Each string defines a parsable directory structure.
        excludes: List[str] (default: [])
            The directory structure that is used to exclude directories from the input directory.
        import_id: str (default: 'sid')
            The meta key pattern, that is used to reference/identify instances.
        outsource_instances: bool (default: True)
            If True, instances are always outsourced to the instance directory. 
    """

    input_dir: str
    instance_dir: str
    structures: List[str]
    excludes: List[str]
    meta: List[Dict[str, str]]
    import_id: str
    outsource_instances: bool
   
    def task(self) -> None:
        with ConsoleCapture(self.config.logger):
            self.runDataImporter()

    def runDataImporter(self) -> None:

        # scan input definitions
        input_dir = os.path.join(self.config.data.abspath, self.input_dir)
        instances_dir = os.path.join(self.config.data.abspath, self.instance_dir)
        structures = self.structures
        excludes = self.excludes

        # print overview in debug mode
        if self.config.debug:
            print("> input_dir...", input_dir)
            print("> structure...", structures)
            print("> excludes....", excludes)

        # scan directory and parse imports and meta data from (deep) folder structure
        sr = scan_directory(input_dir, structures, excludes, verbose=self.config.verbose)
        
        # extend meta from csv
        if meta_extends := self.meta:
            for me in meta_extends:
                if me['type'] == 'csv' and 'id' in me and 'path' in me and os.path.isfile(me['path']):
                    extend_meta_from_csv(sr, me['path'], me['id'])

        # collect created instances and bundles
        instances: Dict[str, Instance] = {}
        bundles: Dict[str, InstanceDataBundle] = {}
       
        # the meta key that is used to reference/identify instances
        import_id_str: str = self.import_id
        import_id_pattern: List[str] = import_id_str.split('/')

        # detect instances that are imported from a data import level 
        unwrapped_instance_paths = get_unwrapped_instance_paths_from_scan_results(sr)

        # create instances
        for s in sr:
            if not s['dtype'] == 'instance':
                continue

            path = s['path']
            meta = s['meta']

            assert isinstance(meta, dict)
            assert isinstance(path, str)

            # construct instance reference from import id pattern
            ref = "/".join([meta[p] for p in import_id_pattern if p in meta])

            # NOTE: when initializing an Instance object, a random id attribute is generated.
            #       in the absence of any other id meta field (e.g., sid, pid...) it wouuld make sense to use this id 
            #       (e.g., for file-based imports like image.nii@instance@nifti)
            #       However, in that case the id must be known prior to the instance creation. 
            #       We therfore generate a random id for each file that matches a structure and populate it via meta['id']. 
            #       In case an id is manually specified in the import structure, this will override the randomly generated id.
            #       Working on a per-file basis, the same id is shared across all data/instance imports for that file. Hence, 
            #       this only makes sense for the file-based instance import as described above and a more subtle aproach would be nice.
            #       We use _instance aas the pseudo meta field.

            # outsource instace base directory (all instance related files will be organized in that directory)
            # warning if instance has no root directory but a data import path (e.g., file or dicom folder)
            if path in unwrapped_instance_paths or self.outsource_instances:

                if path in unwrapped_instance_paths:
                    print(f"WARNING: instance definition on dtype import level is experimental: {path}")

                # make dir
                instance_dir = os.path.join(instances_dir, ref)

                # instance dir must be unique
                assert not os.path.isdir(instance_dir), f"Error: instance dir {instance_dir} already exists."

                # create instance dir
                os.makedirs(instance_dir)

                # update path
                path = instance_dir

            # create instance
            if not ref in instances:
                instances[ref] = Instance(path=path)
                instances[ref].attr['_ref'] = ref
                for k, v in meta.items():
                    if k == '_instance': k = 'id'
                    instances[ref].attr[k] = v

        # create bundles
        for s in sr:
            if not s['dtype'] == 'bundle':
                continue

            assert 'bundle' in s and isinstance(s['bundle'], str)
            assert isinstance(s['bundle'], str)
            assert isinstance(s['meta'], dict)
            assert isinstance(s['path'], str)

            path = s['path']
            meta = s['meta']
            bundle_id = s['bundle']

            # without further checks, bundle definition on file level is forbidden
            assert os.path.isdir(path), f"Error: bundle definition on file level is forbidden: {path}"

            # make sure bundles are created only once
            if bundle_id in bundles:
                continue

            # construct instance reference from import id pattern
            ref = "/".join([meta[p] for p in import_id_pattern if p in meta])

            # get instance
            assert ref in instances, f"Error: instance {ref} not found."
            instance = instances[ref]

            # create bundle
            bundle = instance.getDataBundle(path)
            bundles[bundle_id] = bundle

        # import data
        # FIXME: imports are always absolute paths (thus always a dc entrypoint)
        for s in sr:

            assert isinstance(s['meta'], dict)
            assert isinstance(s['path'], str)
            assert isinstance(s['dtype'], str)

            path = s['path']
            meta = s['meta']
            dtype_def = s['dtype']

            # ignore instance creations (done in previous step)
            if dtype_def.upper() in ['INSTANCE', 'BUNDLE']:
                continue

            # TODO: optionally copy data into (newly created) instance dir?
            #       Nicer structure but likely adding complexity and not needed as imported files are considered read-only.

            # create data    
            dtype = DataType.fromString(dtype_def)
            dtype.meta += {k: v for k, v in meta.items() if not k.startswith('_')}
            instance_data = InstanceData(path, dtype)

            # append data
            if "_bundle" in meta:
                #  get bundle
                bundle_id = str(meta['_bundle'])
                assert bundle_id in bundles, f"Error: bundle {bundle_id} not found."
                bundle = bundles[bundle_id]

                # add data to bundle
                bundle.addData(instance_data)
            else:
                # get instance
                ref = "/".join([meta[p] for p in import_id_pattern if p in meta])
                if ref not in instances:
                    print("ref", ref)
                    print("instances", instances)
                assert ref in instances, f"Error: instance {ref} not found. \n" + "\n".join(instance for instance in instances)
                instance = instances[ref]

                # add data to instance
                instance.addData(instance_data)

            # confirm instance data
            if os.path.exists(instance_data.abspath):
                instance_data.confirm()

        # add instances to datahandler
        self.config.data.instances = list(instances.values())


def get_unwrapped_instance_paths_from_scan_results(sr: List[ScanFeature]) -> List[str]:
    sr_path_group_dtypes: Dict[str, List[str]] = {}
    for s in sr:
        if not s['path'] in sr_path_group_dtypes:
            sr_path_group_dtypes[s['path']] = []
        
        if s['dtype'] not in sr_path_group_dtypes[s['path']]:
            sr_path_group_dtypes[s['path']].append(s['dtype'])

    return [s['path'] for s in sr if len(sr_path_group_dtypes[s['path']]) > 1 and s['dtype'] == 'instance']


def scan_directory(start_dir: str, structures: List[str], excludes: List[str], meta: Optional[Dict[str, str]] = None, verbose: bool = False) -> List[ScanFeature]:
    """
    Scan a directory for files and import them.
    Parse metadata from the folder structure.
    """

    # split structures into components
    sps = [structure.split('/') for structure in structures]
    eps = [exclude.split('/') for exclude in excludes]

    # return list with all imports
    imports = []

    # scan directory
    for dir in os.listdir(start_dir):

        # init meta
        if meta is None:
            _meta: Dict[str, str] = {}
        else:
            _meta: Dict[str, str] = copy.deepcopy(meta)

        # debug the meta dict (always be careful with referenced objects in recursive functions...)
        # print(f"\n~> start meta: ({id(_meta)}) {_meta} for {os.path.join(start_dir, dir)}")

        # find matching structures (always match $xx placeholders and remove @dtype import instructioms before matching)
        # matching_structures = [sp for sp in sps if len(sp) and (sp[0].startswith('$') or dir == sp[0].split('@')[0].split('$')[0])]
        matching_excludes = [ep for ep in eps if len(ep) and (ep[0].startswith('$') or dir == ep[0])]

        # exclude (ignore dir) if matching exclude leaf reached
        matching_exclude_leafs = [e for e in matching_excludes if len(e) == 1]
        if len(matching_exclude_leafs) > 0:
            if verbose:
                print(f"EXCLUDE: {dir} due to matching exclude leafs: {matching_exclude_leafs}")
            continue

        # filter matching structure 
        ms_placeholder = [sp for sp in sps if len(sp) and sp[0].startswith('$')]
        ms_filter = [sp for sp in sps if len(sp) and dir == sp[0].split('@')[0].split('$')[0]]
        ms_regex = [sp for sp in sps if len(sp) and sp[0].startswith('re:') and re.fullmatch(sp[0][3:].split('::')[0], dir)]

        #  The resuting set may contain either only placeholders or a single filter matching `dir`.
        #  Thereby, explicit exceptions from the placeholder directive are enabled.
        matching_structures = ms_regex or ms_filter or ms_placeholder 

        # A] Filter / Placeholder 
        if len(ms_regex) == 0:

            # extract meta keys
            keys = {
                *{s[0].split('@')[0] for s in matching_structures if s[0].startswith('$')},
                *{'$' + s[0].split('$')[1].split('@')[0] for s in matching_structures if '$' in s[0]}
            }

            # exclude directory if any placeholder differs from meta value on same key (> no meta overloading)
            #   e.g., inherited meta[sid] = A, evaluated dir = 'B' and $sid is in keys  -> exclude (A != B)
            #   e.g., inherited meta[sid] = A, evaluated dir = 'A' and $sid in keys     -> ok      (A == B)
            #   e.g., inherited meta[sid] = A, evaluated dir = 'B' and $sid not in keys -> ok      (no overloading)
            if len([k for k in keys if k in _meta and _meta[k] != dir]) > 0:
                if verbose:
                    print(f"EXCLUDE: {dir} due to placeholder mismatch")
                continue
            
            # extract imports
            # FIXME: using a set ensures uniqueness but causes arbitrary order, causing an error when data import occures before instance import for file-instance scenarios
            #imps = {s[0].split('@')[i] for s in matching_structures for i in range(1, s[0].count('@') + 1) if '@' in s[0]}
            imps = [s[0].split('@')[i] for s in matching_structures for i in range(1, s[0].count('@') + 1) if '@' in s[0]]

            # make imps unique
            imps = list(dict.fromkeys(imps))

            # extend current meta data by extracted keys from current iteration level
            _meta: Dict[str, str] = {
                **_meta,
                **{key[1:]: dir for key in keys if len(key) > 0}
            }
        
        # B] Regex
        else:
            verbose_regex = True

            if verbose_regex: print("┌───────── REGEX ─────────")
            if verbose_regex: print("│ evaluate: ", dir)
            if verbose_regex: print("│")

            # collect imports
            imps = []
            keys = []       # <-- dummy, only for printing
            _matching_structures = []

            # iterate through matching regex structures
            for ms in matching_structures:
                if verbose_regex: print("│", ms[0])

                # extract regex pattern and group definitions
                regex_pattern, *groups = ms[0][3:].split("::")

                if verbose_regex: print("│ ├─", regex_pattern)
                if verbose_regex: print("│ └─", groups)

                # match regex
                match = re.fullmatch(regex_pattern, dir)
                assert match is not None

                # collect import and meta placeholsers on match level
                #   if a filter in on of the groups unmatches, discard the whole match
                match_imps = []
                match_meta = {}
                match_pass = True

                # iterate all groups of the regex
                groups_n = len(match.groups()) - 1
                for group_i, group in enumerate(groups):
                    if group_i <= groups_n:
                        group_v = match.group(group_i + 1)
                        if verbose_regex: print("│ │   └─ ", group_i, group, group_v)

                        if '$' in group:                 # placeholder
                            group_p = group.split('$')[1].split('@')[0]
                            if group_p in _meta and _meta[group_p] != group_v:
                                raise Exception(f"Meta overload in regex: {group_p}: <- {group_v} != {_meta[group_p]} in {dir} (regex: {regex_pattern})")
                            match_meta[group_p] = group_v
                            keys.append(group_p)
                        
                        if not group.startswith('$'):     # filter
                            group_f = group.split('$')[0]
                            if group_v != group_f:
                                if verbose_regex: print("│ │   └─ ", f"𐄂    (filter unmatch: {group_v} != {group_f})")
                                match_pass = False  
                                break
                        
                        if '@' in group:                # import (within group evaluation)
                            match_imps += group.split('@')[1:]

                    elif group.startswith('@'):         # import (outside of group evaluation, last overlapping statement)
                        assert group != '@instance', f"Error: regex instance import must be bound to a placeholder variable."
                        match_imps.append(group[1:])

                # update imps and meta with all imps and meta extraced from regex 
                #   only if the regex match passed all potential filters    
                if match_pass:
                    imps += match_imps
                    _meta = {**_meta, **match_meta}
                    _matching_structures.append(ms)

                if verbose_regex: print("│")
            if verbose_regex: print("│ ────────────────────────")
            if verbose_regex: print("│ meta:   ", _meta)
            if verbose_regex: print("│ imps:   ", imps)
            if verbose_regex: print("└─────────────────────────")

            # update matching structures
            #   include a structure only if the regex at position 0 passed evaluation on all group filters
            matching_structures = _matching_structures

        # print parsing results
        if verbose:
            print(f"dir {dir:<15}, keys {str(keys):<20}, imp: {str(imps):<10}, s: {', '.join(['/'.join(s) for s in matching_structures]):<60}, m: {':'.join(f'{k}={v}' for k, v in _meta.items())}")

        # stop or recurse
        stop = False
        if len(imps) > 0:    # if import statement found (@dtype) stop recursion and return current meta

            # generate a random id
            import_id = str(uuid.uuid4())

            for i, imp in enumerate(imps):

                # print import stop
                if verbose:
                    print(f"IMPORT ({i+1}/{len(imps)}) [{imp}|{os.path.join(start_dir, dir)}]: {':'.join(f'{k}={v}' for k, v in _meta.items())}")


                # instance import
                if imp == 'instance':
                    instance_id = str(uuid.uuid4())

                    if os.path.isfile(os.path.join(start_dir, dir)) and verbose:
                        print("> WARNING: instance import on file level. Instacnes need a base folder that must be created in that case. Random instance_id can be used as ref, set import_id: _instance in config.")

                    imports.append({
                        'path':     os.path.join(start_dir, dir),
                        'meta':    {'_instance': instance_id, **_meta},
                        'dtype':    'instance'
                    })
                    _meta: Dict[str, str] = {
                        **_meta,
                        '_instance': instance_id
                    }

                # bundle import
                elif imp == "" or imp == "bundle":
                    bundle_id = str(uuid.uuid4())
                    imports.append({
                        'path':     os.path.join(start_dir, dir),
                        'meta':     _meta,
                        'dtype':    'bundle',
                        'bundle':   bundle_id
                    })
                    _meta: Dict[str, str] = {
                        **_meta,
                        **{'_bundle': bundle_id}
                    }

                # data import
                else:
                    imports.append({
                        'path':     os.path.join(start_dir, dir),
                        'meta':     _meta,
                        'dtype':    imp
                    })

                    # stop recursion after data import
                    stop = True
       
        # recurse into directory if dir is not a leaf node (file) already or if stop signal is set by data import statement
        # pass the current _meta context to the next recursion level
        # pass the remaining structures and excludes to the next recursion level
        if not stop and os.path.isdir(os.path.join(start_dir, dir)): 
            if nested_imports := scan_directory(
                os.path.join(start_dir, dir), 
                ["/".join(s[1:]) for s in matching_structures], 
                ["/".join(e[1:]) for e in matching_excludes],
                _meta, 
                verbose
            ):
                
                # Remove all instance imports from any parent directory.
                # NOTE: Although a single statement can only have a single instance import, 
                #       another statement might have an instance import at a different poition 
                #       and if those statements share some matching filters / placeholders, 
                #       multiple import statmenets can trigger. 
                # NOTE: Instead of filtering parent imports on every recursive iteration, 
                #       filtering the final imports list might be more efficient.
                for n in nested_imports:
                    if n['dtype'] == 'instance':
                        for i in imports:
                            if i['dtype'] == 'instance' and os.path.commonprefix([str(i['path']), str(n['path'])]) == i['path']:
                                    imports.remove(i)

                # add nested imports to imports collection
                imports += nested_imports
            
    # return
    return imports


def extend_meta_from_csv(scan_results: List[ScanFeature], csv_path: str, id: str) -> None:
    """
    Extend the meta data of the scan results with the content of a csv file.
    """

    # read csv into a id -> {k: v} dictionary structure
    ext_meta = {}
    with open(csv_path, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            ext_meta[row[id]] = {k: v for k, v in row.items() if k != id and v}

    # extend meta data
    for scan_result in scan_results:
        assert isinstance(scan_result['meta'], dict)
        if id in scan_result['meta']:
            ref = scan_result['meta'][id]

            scan_result['meta'] = {
                **scan_result['meta'],
                **ext_meta[ref]
            }
