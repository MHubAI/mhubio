"""
-------------------------------------------------
MHub - UniversalImporter 
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

from typing import List, Dict, Optional, Union
from mhubio.core import Config, Meta, Module, Instance, InstanceData, InstanceDataBundle, DataType, FileType
import os, csv, copy, uuid

ScanFeature = Dict[str, Union[str, Dict[str, str]]]

class UniversalImporter(Module):
    """
    Universal Importer Module.
    Import data from a variety of sources.
    """

    def __init__(self, config: Config):
        super().__init__(config)

    
    def task(self) -> None:
        # scan input definitions
        input_dir = self.getConfiguration('input_dir', '')
        input_dir = os.path.join(self.config.data.abspath, input_dir)
        structures = self.getConfiguration('structures', [])
        excludes = self.getConfiguration('excludes', [])

        # print overview in debug mode
        if self.config.debug:
            print("> input_dir...", input_dir)
            print("> structure...", structures)
            print("> excludes....", excludes)

        # scan directory and parse imports and meta data from (deep) folder structure
        sr = scan_directory(input_dir, structures, excludes, verbose=self.config.verbose)
        
        # extend meta from csv
        if meta_extends := self.getConfiguration('meta', None):
            for me in meta_extends:
                if me['type'] == 'csv' and 'id' in me and 'path' in me and os.path.isfile(me['path']):
                    extend_meta_from_csv(sr, me['path'], me['id'])

        # collect created instances and bundles
        instances: Dict[str, Instance] = {}
        bundles: Dict[str, InstanceDataBundle] = {}
       
        # the meta key that is used to reference/identify instances
        import_id = self.getConfiguration('import_id', None) or 'sid'

        # create instances
        for s in sr:
            if not s['dtype'] == 'instance':
                continue

            path = s['path']
            meta = s['meta']
        
            if not import_id in meta:
                print("Warning: no import id found in meta data. Skipping import.")
                continue

            assert isinstance(meta, dict)
            ref = meta[import_id]

            # create instance
            assert isinstance(path, str)
            if not ref in instances:
                instances[ref] = Instance(path=path)
                for k, v in meta.items():
                    instances[ref].attr[k] = v

        # create bundles
        for s in sr:
            if not s['dtype'] == 'bundle':
                continue

            path = s['path']
            meta = s['meta']
            bundle_id = str(s['bundle'])

            # make sure bundles are created only once
            if bundle_id in bundles:
                continue

            # get reference from meta via import_id key
            if not import_id in meta:
                print("Warning: no import id found in meta data. Skipping import.")
                continue

            assert isinstance(meta, dict)
            ref = meta[import_id]

            # get instance
            assert ref in instances, f"Error: instance {ref} not found."
            instance = instances[ref]

            # create bundle
            bundle = instance.getDataBundle(bundle_id)
            bundles[bundle_id] = bundle

        # import data
        for s in sr:
            path = s['path']
            meta = s['meta']
            ftype_def = str(s['dtype']).upper() # FIXME: use ftype instaed of dtype for consistency

            # ignore instance creations (done in previous step)
            if ftype_def in ['INSTANCE', 'BUNDLE']:
                continue

            if not import_id in meta:
                print("Warning: no import id found in meta data. Skipping import.")
                continue

            # create data
            assert isinstance(path, str) and isinstance(meta, dict)        
            assert ftype_def in FileType.__members__, f"{ftype_def} not a valid file type."
            ftype = FileType[ftype_def]
            instance_data_type = DataType(ftype, Meta() + meta)
            instance_data = InstanceData(path, instance_data_type)

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
                ref = meta[import_id]
                assert ref in instances, f"Error: instance {ref} not found."
                instance = instances[ref]

                # add data to instance
                instance.addData(instance_data)

        # add instances to datahandler
        self.config.data.instances = list(instances.values())


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
        matching_structures = [sp for sp in sps if len(sp) and (sp[0].startswith('$') or dir == sp[0].split('@')[0].split('$')[0])]
        matching_excludes = [ep for ep in eps if len(ep) and (ep[0].startswith('$') or dir == ep[0])]

        # exclude (ignore dir) if matching exclude leaf reached
        matching_exclude_leafs = [e for e in matching_excludes if len(e) == 1]
        if len(matching_exclude_leafs) > 0:
            if verbose:
                print(f"EXCLUDE: {dir} due to matching exclude leafs: {matching_exclude_leafs}")
            continue
        
        # extract meta keys
        keys = {
            *{s[0].split('@')[0] for s in matching_structures if s[0].startswith('$')},
            *{'$' + s[0].split('$')[1].split('@')[0] for s in matching_structures if '$' in s[0]}
        }

        # extract imports
        imps = {s[0].split('@')[1] for s in matching_structures if '@' in s[0]}

        # extend current meta data by extracted keys from current iteration level
        _meta: Dict[str, str] = {
            **_meta,
            **{key[1:]: dir for key in keys if len(key) > 0}
        }

        # print parsing results
        if verbose:
            print(f"dir {dir:<15}, keys {str(keys):<20}, imp: {str(imps):<10}, s: {', '.join(['/'.join(s) for s in matching_structures]):<60}, m: {':'.join(f'{k}={v}' for k, v in _meta.items())}")

        # stop or recurse
        stop = False
        if len(imps) > 0:    # if import statement found (@dtype) stop recursion and return current meta
            for i, imp in enumerate(imps):

                # print import stop
                if verbose:
                    print(f"IMPORT ({i+1}/{len(imps)}) [{imp}|{os.path.join(start_dir, dir)}]: {':'.join(f'{k}={v}' for k, v in _meta.items())}")


                # instance import
                if imp == 'instance':
                    imports.append({
                        'path':     os.path.join(start_dir, dir),
                        'meta':     _meta,
                        'dtype':    'instance'
                    })

                # bundle import
                elif imp == "":
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
