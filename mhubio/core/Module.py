"""
-------------------------------------------------
MHub - Module base class for the mhubio framework
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (27.02.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import Any, List, Type, Optional
from .Config import Config

import time

class Module:
    # label:    str
    # config:   Config
    # verbose:  bool
    # debug:    bool

    def __init__(self, config: Config, local_config: Optional[dict] = None) -> None:
        self.label: str = self.__class__.__name__
        self.config: Config = config
        self.verbose: bool = config.verbose
        self.debug: bool = config.debug
        self.local_config: dict = local_config if local_config is not None else {}

    @property 
    def c(self) -> Any:
        return self.config[self.__class__]
    
    def getConfiguration(self, key: str, default: Any = None) -> Any:
        try:
            if key in self.local_config:
                return self.local_config[key]
            else:
                # NOTE: this might fail --> try/catch except block them returns default value
                return self.c[key]
        except:
            return default

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