"""
-------------------------------------------------
MHub - Logger Class for console and file logging
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
Date: 31.08.2023
-------------------------------------------------
"""

from enum import Enum
from typing import List, Optional, Union
from .Instance import Instance
from .Config import Config
from .InstanceData import InstanceData
from .DataType import DataType
from .FileType import FileType

import os, sys, time, statistics

class ConsoleCapture:
    def __init__(self, logger: Optional['MLog'], display_on_console=False):
        self.logger = logger
        self.display_on_console = display_on_console
        self.buffer = ""
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def __enter__(self):
        if self.logger is None: 
            return self
        
        sys.stdout = self
        sys.stderr = self
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.logger is None: 
            return
        
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

        if len(self.buffer):
            assert "/n" not in self.buffer, "Buffer should not contain newlines."
            self.logger.log(self.buffer, level=MLogLevel.CAPTURED)

    def buff(self, text: str):
        if not self.logger:
            return
        
        self.buffer += text
        lines = self.buffer.split("\n")
        self.buffer = lines[-1]

        for line in lines[:-1]:
            self.logger.log(line, level=MLogLevel.CAPTURED)

    def write(self, message):
        if message:
            if sys.stdout == self:
                self.buff(message)

            elif sys.stderr == self:
                self.buff(message)
            
            if self.display_on_console:
                self.original_stdout.write(message)
                self.original_stdout.flush()

def format_seconds(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    if d > 0:
        return "%d:%02d:%02d:%02d" % (d, h, m, s)
    elif h > 0:
        return "%d:%02d:%02d" % (h, m, s)
    else:
        return "%d:%02d" % (m, s)

class MLogLevel(str, Enum):
    NOTICE = 'NOTICE'
    WARNING = 'WARNING'
    DEPRECATED = 'DEPRECATED'
    ERROR = 'ERROR'
    DEBUG = 'DEBUG'
    EXTERNAL = 'EXTERNAL'
    CAPTURED = 'CAPTURED'

    # print level
    def __str__(self):
        return self.name

class MLog:

    def __init__(self, config: Config) -> None:
        self.showProgress = True
        self.config: Config = config
        self.started: bool = False

        # list of modules and current module's label
        #  We gradually increase the progres, as module labels must not be unique per workflow, however using module instances requires to initialize them at step registration (we may considder this for improved caching in the future and then update the MLog class accordingly)
        self.steps: List[str] = []
        self.module: Optional[str] = None
        self.progress: int = 0

        # list of instances, current instance (reference) and instance progress
        #  the instance progress is always within the scope of the current module
        self.instances: int = 0
        self.instance_progress: int = 0
        self.instance: Optional[Instance] = None

        # counding the number of characters printed to the console
        self.nchp: int = 0

        # collecting timing information
        self.timing = {}

        # cache log messages per module and instance.
        #  As long as there is a current module but no instance, log messages are stored in the module (which then will be populated as a file on the global instance once the module is finished). If there is an instance, we instead append the log messages to the instance's log cache which will be populated on the instance once the instance is finished.
        self.global_log_cache = []
        self.module_log_cache = []
        self.instance_log_cache = []


    def p(self, *args, **kwargs):
        """Internal printing method to keep track of printed characters.
        """
        msg = " ".join([str(arg) for arg in args])
        self.nchp += len(msg) + 1
        print(msg, **kwargs)

    def registerModule(self, module: str):
        """Register a module.

        Args:
            module (str): Pass the module's label (Module.label) to register it with the logger.
        """

        assert not self.started, "Cannot register modules after starting."
        self.steps.append(module)

    def start(self):
        """Start the logger.
            Only once the logger is started you can start modules.
        """
        self.updateProgress()
        self.started = True

    def startModule(self, module: str):
        """Start a module and update the progress.
            Only once a module is started you can start instances.
        """
        
        # sanity checks
        assert self.started, "Cannot start module before starting the logger."
        assert module in self.steps, "Cannot start module that is not registered."
        assert self.module is None, "Cannot start module if another module is already started."

        # update progress and time
        self.module = module
        self.timing[module] = {
            "start": time.time(),
            "stop": None,
            "instances": {},
            "instance_average": 0,
            "num_instances_completed": 0
        }

        # update progressbar on console
        self.updateProgress()

    def finishModule(self, module: str):
        """Stop a module and update the progress.
            You need to stop the current module before starting the next module.
        """
        
        # sanity checks
        assert self.started, "Cannot finish module before starting the logger."
        assert module in self.steps, "Cannot finish module that is not registered."
        assert self.module == module, "Cannot finish module that is not the current module."

        # export module log
        self.exportModuleLog()

        # update progress and time
        self.module = None
        self.progress += 1
        self.timing[module]["stop"] = time.time()
        self.timing[module]["num_instances_completed"] = len(self.config.data.instances)

        # update progressbar on console
        self.updateProgress()

    def startInstance(self, instance: Instance):
        """Start an instance and update the progress.
            An instance can only be started once the logger and a module are started.

        Args:
            instance (Instance): The instance currently processed.
        """

        # sanity checks
        assert self.started, "Cannot start instance before starting the logger."
        assert self.instance is None, "Cannot start instance if another instance is already started."
        assert self.module is not None, "Cannot start instance if no module is started."
        
        # update progress and time
        self.instance = instance
        self.instances = len(self.config.data.instances)
        self.instance_progress = self.config.data.instances.index(instance)
        self.timing[self.module]["instances"][instance] = {
            "start": time.time(),
            "stop": None
        }

        # update progressbar on console
        self.updateProgress()

    def finishInstance(self, instance: Instance):
        """Stop an instance and update the progress.
            You need to stop the current instance before starting the next instance.

        Args:
            instance (Instance): The instance finished.
        """

        # sanity checks
        assert self.started, "Cannot finish instance before starting the logger."
        assert self.instance == instance, "Cannot finish instance that is not the current instance"
        
        # export instance log
        self.exportInstanceLog()

        # update progress and time
        self.instance = None
        self.instance_progress += 1
        self.timing[self.module]["instances"][instance]["stop"] = time.time()
        self.timing[self.module]["instance_average"] = statistics.mean(i['stop'] - i['start'] for i in self.timing[self.module]["instances"].values())

        # update progressbar on console
        self.updateProgress()

    def updateProgress(self):
        """Print a progress bar to the console.
        """

        if not self.showProgress:
            return

        MODULE_NAME_LEN = 27
        PROGRESS_BAR_LEN = 15

        # clean console
        if self.started:
            for _ in range(len(self.steps)):
                print("\x1b[1A\x1b[2K", end="")

        # print console timeline
        for i, module in enumerate(self.steps):
            # print all modules in gray but the current module in blue
            if i == self.progress:
                print("\x1b[36m", end="")
            else:
                print("\x1b[90m", end="")

            # print module
            self.p(str(i+1) + ". " + module, end="")
            
            # reset color
            print("\x1b[0m", end="")

            # add padding
            self.p(" " * (MODULE_NAME_LEN - len(module)), end="")

            if i == self.progress and self.instances:
                
                # print progres bar for instances
                p = self.instance_progress / self.instances
                self.p("[" + "#" * int(p * PROGRESS_BAR_LEN) + " " * (PROGRESS_BAR_LEN - int(p * PROGRESS_BAR_LEN)) + "]", end="")

                # add x/n indicator
                self.p(" %s/%s"%(self.instance_progress, self.instances),  end="")

                # print instance id / sid
                # if self.instance is not None:
                #     if 'sid' in self.instance.attr:
                #         self.p(" (%s)"%self.instance.attr['sid'], end="")
                #     elif 'id' in self.instance.attr:
                #         self.p(" (%s)"%self.instance.attr['id'], end="")

                # estimate time
                if self.instance_progress == 0:
                    self.p("  eta ~?", end="")
                elif module in self.timing and self.timing[module]["instance_average"] is not None:
                    n_remaining = self.instances - self.instance_progress + 1
                    t_remaining = n_remaining * self.timing[module]["instance_average"]
                    self.p(f"  eta ~{format_seconds(t_remaining)}", end="")

            else:

                # print time
                if module in self.timing and self.timing[module]["stop"] is not None:
                    elapsed = self.timing[module]["stop"] - self.timing[module]["start"]
                    self.p(f"({format_seconds(elapsed)})", end="")

                # print x/n instances
                if module in self.timing:
                    n_inst = self.timing[module]["num_instances_completed"]
                    self.p(" %s/%s"%(n_inst, n_inst), end="")

            # add newline
            self.p()


    def log(self, *args, level: Union[str, MLogLevel] = MLogLevel.NOTICE):
        """Log a message. 

        By default, all messsages are logged into a file, bound to the current module and instance (if available). All calls to `Module.v()` and `Module.log()` are redirected to this method.

        If starting a workflow from the mhubio.run module (which is the default entrypoint for all MHub models), you can specify CLI commands to overwrite the default logging behaviour. The following commands are available:

        --print 
            bypass file logging and instead print all messages directly to the console. This is useful for development and if you plan to route all console outputs to a single file.

        --debug
            omit the progressbar and instead print an instance overview after each module's execution.

        --print --debug
            print all messages including an instance overview to the console and omit the progressbar. 

        Args:
            level (Union[int, MLogLevel], optional): The level of the log message. Defaults to MLogLevel.NOTICE.
        """
        # convert int level to MLogLevel
        if isinstance(level, str):
            level = MLogLevel(level)

        # get timestamp and format to dd.mm.yy hh:mm:ss
        timestamp = time.time()
        timestamp = time.strftime("%d.%m.%y %H:%M:%S", time.localtime(timestamp))

        # construct message
        msg = " ".join([str(arg) for arg in args])
        msg = f"[{str(level)}|{timestamp}]: {msg}"

        # collect all log messages
        self.cacheLogMessage(msg)

    def cacheLogMessage(self, msg):
        if self.module and not self.instance:
            self.module_log_cache.append(msg)
        elif self.module and self.instance:
            self.instance_log_cache.append(msg)
        else:
            self.global_log_cache.append(msg)

    @staticmethod
    def exportLog(mlabel: str, instance: Instance, log: List[str]): 
        # sanity checks
        assert instance is not None, "Cannot export instance log if no instance is started."
        assert mlabel is not None, "Cannot export instance log if no module is started."

        #create InstanceData 
        mlog_file = mlabel + '.log'
        mlog_bundle = instance.getDataBundle('mhub_log')
        mlog_meta = {'module': mlabel}
        mlog_data = InstanceData(mlog_file, DataType(FileType.LOG, mlog_meta), instance=instance, bundle=mlog_bundle, auto_increment=True)

        # create bundle and file
        mlog_data.dc.makedirs()
        open(mlog_data.abspath, 'a').close()

        # write instance cache to file
        with open(mlog_data.abspath, 'w') as f:
            for msg in log:
                f.write(msg + "\n")

        # confirm module log data if file was created and is not empty
        if os.path.isfile(mlog_data.abspath) and os.path.getsize(mlog_data.abspath) > 0:
                mlog_data.confirm()

    def exportInstanceLog(self):
        assert self.instance is not None, "Cannot export instance log if no instance is started."
        assert self.module is not None, "Cannot export instance log if no module is started."

        if len(self.instance_log_cache):
            self.exportLog(self.module, self.instance, self.instance_log_cache)
            self.instance_log_cache = []

    def exportModuleLog(self):
        assert self.module  is not None, "Cannot export module log if no module is started."

        if len(self.module_log_cache):
            self.exportLog(self.module, self.config.data.globalInstance, self.module_log_cache)
            self.module_log_cache = []