"""
-------------------------------------------------
MHub - Config, Instance & Data Classes
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""


from typing import Union, Optional, Type, Any
import os, yaml

def dict_merge(source: dict, destination: dict) -> dict:
    for k, v in source.items():
        if isinstance(v, dict):
            n = destination.setdefault(k, {})
            dict_merge(v, n)
        else:
            destination[k] = v
    return destination


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

from .DataHandler import DataHandler
from .Module import Module