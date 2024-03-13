"""
-------------------------------------------------
MHub - Module base class for the mhubio framework
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (27.02.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import Any, List, Type, Optional, Union
from .Config import Config
from .Logger import MLogLevel

import time, subprocess

class Module:
    # label:    str
    # config:   Config
    # verbose:  bool
    # debug:    bool

    def __init__(self, config: Config, local_config: Optional[dict] = None) -> None:
        self.label: str = self.__class__.__name__
        self.config: Config = config
        self.local_config: dict = local_config if local_config is not None else {}
        self.log = ModuleLogger(module=self)

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
        """
        Legacy method for logging. Resolves to log(file=True).
        """
        self.log.notice(*args)

    def subprocess(self, args: List[str], **kwargs) -> None:

        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, universal_newlines=True, **kwargs) as p:
            if p.stdout:
                for line in p.stdout:
                    self.log(line.strip(), level=MLogLevel.EXTERNAL)


    def execute(self) -> None:
        # new MLog implementation
        if self.config.logger is not None:
            self.config.logger.startModule(self.label)

        # old logging
        self.v("\n--------------------------")
        self.v("Start %s"%self.label)
        start_time = time.time()
        self.task()
        elapsed = time.time() - start_time
        self.v("Done in %g seconds."%elapsed)

        # new MLog implementation
        if self.config.logger is not None:
            self.config.logger.finishModule(self.label)

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
            
            
class ModuleLogger():
    """
    Convenience class to log messages from a module.
    """

    def __init__(self, module: Module) -> None:
        self.module = module
        self.logger = module.config.logger

    @property 
    def active(self) -> bool:
        return self.logger is not None

    def log(self, *args, level: Union[str, MLogLevel] = MLogLevel.NOTICE) -> None:
        """Passes a log message down to the MLog logger instance.

        Args:
            level (Union[str, MLogLevel], optional): The type of the log message. Defaults to MLogLevel.NOTICE.
        """
        if self.logger is not None:
            self.logger.log(*args, level=level)
        else:
            print(*args)
        
    def __call__(self, *args, level: Union[str, MLogLevel] = MLogLevel.NOTICE) -> Any:
        """Shortcut for self.log() method.

        Args:
            level (Union[str, MLogLevel], optional): The type of the log message. Defaults to MLogLevel.NOTICE.
        """
        self.log(*args, level=level)
         
    def notice(self, *args) -> None:
        self.log(*args, level=MLogLevel.NOTICE)
        
    def warning(self, *args) -> None:
        self.log(*args, level=MLogLevel.WARNING)
        
    def deprecated(self, *args) -> None:
        self.log(*args, level=MLogLevel.DEPRECATED)
        
    def error(self, *args) -> None:
        self.log(*args, level=MLogLevel.ERROR)
        
    def debug(self, *args) -> None:
        self.log(*args, level=MLogLevel.DEBUG)
        
    def external(self, *args) -> None:
        self.log(*args, level=MLogLevel.EXTERNAL)
        
    def captured(self, *args) -> None:
        self.log(*args, level=MLogLevel.CAPTURED)
        