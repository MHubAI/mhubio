"""
-------------------------------------------------
MHub - MHubIO Runner (entrypoint).
python3 -m mhubio.run 
    --debug
    --cleanup
    --config path/to/config.yml
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import Dict, List, Optional, Union, Any, Tuple, Type
import sys, os, importlib, yaml, shutil
from mhubio.core import Config, Module
from enum import Enum

# define import paths
import_paths = {
    'DicomImporter': 'mhubio.modules.importer.DicomImporter',
    'NrrdImporter': 'mhubio.modules.importer.NrrdImporter',
    'FileStructureImporter': 'mhubio.modules.importer.FileStructureImporter',
    'FileListImporter': 'mhubio.modules.importer.FileListImporter',

    'AttributeFilter': 'mhubio.modules.filter.AttributeFilter',

    'DicomConverter': 'mhubio.modules.convert.DicomConverter',
    'NiftiConverter': 'mhubio.modules.convert.NiftiConverter',
    'NiftiConverter2': 'mhubio.modules.convert.NiftiConverter2',
    'NrrdConverter': 'mhubio.modules.convert.NrrdConverter',
    'DsegConverter': 'mhubio.modules.convert.DsegConverter',

    'DataOrganizer': 'mhubio.modules.organizer.DataOrganizer',

    'NNUnetRunner': 'mhubio.modules.runner.NNUnetRunner'
}

# define initialization arguments
initialization_arguments = {
    'DataOrganizer': {
        'set_file_permissions': sys.platform.startswith('linux')
    }
}

class f(str, Enum):
    chead       = '\033[95m'
    cyan        = '\033[96m'
    cgray       = '\033[30m'
    cyellow     = '\033[93m'    
    cend        = '\033[0m'
    fitalics    = '\x1B[3m'
    funderline  = '\x1B[4m'
    fnormal     = '\x1B[0m'
    fbold       = '\x1B[1m'

def scan_local_modules() -> Dict[str, str]:
    base_dir = '/app/models'

    local_import_paths = {}

    for model_dir in os.listdir(base_dir):
        model_path = os.path.join(base_dir, model_dir)
        model_utils_path = os.path.join(model_path, 'utils')
        
        if not os.path.isdir(model_utils_path):
            continue

        for module_file in os.listdir(model_utils_path):
            module_path = os.path.join(model_utils_path, module_file)
            if module_path.endswith('.py'):
                module_class_name = module_file[:-3]
                local_import_paths[module_class_name] = f'models.{model_dir}.utils.{module_class_name}'

    return local_import_paths

def scan_configurations() -> List[Dict]:
    root_dir = '/app/models'
    configurations = []

    for model_dir in os.listdir(root_dir):
        configs_path = os.path.join(root_dir, model_dir, 'config')

        if not os.path.isdir(configs_path):
            continue

        for config_file in os.listdir(configs_path):
            if config_file.endswith('.yml'):
                config_path = os.path.join(configs_path, config_file)

                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)

                if 'general' not in config:
                    continue

                configurations.append({
                    'model': model_dir,
                    'config': config_path,
                    'description': config['general']['description'] if 'description' in config['general'] else 'n/a'
                })

    return configurations

def print_configurations(configurations: List[Dict], selection: int = 0, interactive: bool = False) -> Optional[str]:
    print(f'\n{f.chead}Available configurations:{f.cend}\n')
    for i, config in enumerate(configurations):
        s = '>' if interactive and selection == i else ' '
        print(f"{s}   {f.cyan}Model: {config['model']}{f.cend}")
        print(f"     {f.cgray+f.fitalics}{config['description']}{f.fnormal}")
        print(f"     {f.cgray}{config['config']}{f.cend}\n")

def interactive_routine():
    # check support
    try:
        import tty, termios
    except ImportError:
        return None

    # callable to fetch key events
    class _Getch:       
        def __call__(self):
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ch

    # wait until key is pressed
    def waitKey():
        inkey = _Getch()
        k = '?'
        while(1):
            k = inkey()
            if k != '': 
                break
        return ord(k)
    
    # load available configurations
    configurations = scan_configurations()

    # display configurations in interactive mode
    selection = 0
    confirmed = False
    aborted = False
    while not (confirmed or aborted):
        os.system('clear')
        print_configurations(configurations, selection, True)
        key = waitKey()
        if key == 65:
            selection = max(0, selection-1)
        elif key == 66:
            selection = min(len(configurations)-1, selection+1)
        elif key == 13:
            confirmed = True
        elif key == 3:
            aborted = True
    
    # return selected config
    if confirmed:
        return configurations[selection]['config']
    else:
        return None

def cleanup():
    shutil.rmtree("/app/data/sorted_data", ignore_errors=True)
    shutil.rmtree("/app/tmp", ignore_errors=True)
    shutil.rmtree("/app/data/output_data", ignore_errors=True)
    shutil.rmtree("/app/data/imported_instances", ignore_errors=True)

def get_workflow(execute_chain: List[Union[str, Dict]]) -> List[Tuple[str, Dict]]:
    workflow = []
    for module in execute_chain:
        module_name = module if isinstance(module, str) else module['module']
        module_args = {k: v for k, v in module.items() if k != 'module'} if isinstance(module, dict) else {}
        workflow.append((module_name, module_args))
    return workflow

def run(config_file: Optional[str] = None):
    global import_paths

    # scan local modules
    import_paths = {**import_paths, **scan_local_modules()}

    # instantiate config
    config = Config(config_file=config_file)

    # ensure the configuration is valid for stand-alone execution
    if not 'execute' in config._config:
        print(f'{f.cyellow+f.fbold} Warning:{f.fnormal+f.cyellow} No execution chain defined in the configuration file.{f.cend}')
        return

    # parse the module list
    workflow = get_workflow(config._config['execute'])

    # sanity check
    if not all([module[0] in import_paths for module in workflow]):
        print(f'{f.cyellow+f.fbold} Warning:{f.fnormal+f.cyellow} One or more modules in the execution chain are not available. You may use a custom run script insead.{f.cend}')
        for (m, _) in workflow:
            if m not in import_paths:
                print(f'{f.cgray}  - {m}{f.cend}')
        return 

    # sequential execution
    for (class_name, model_config) in workflow:

        mimport = importlib.import_module(import_paths[class_name])
        module: Type[Module] = getattr(mimport, class_name)
        kwargs = initialization_arguments[class_name] if class_name in initialization_arguments else {}

        module(
            config = config, 
            local_config = model_config, 
            **kwargs
        ).execute()

if __name__ == '__main__':

    # interactive mode?
    interactive = '--non-interactive' not in sys.argv

    # check if a config file is provided via the --config argument
    config_file = None
    if '--config' not in sys.argv:

        print('\nPlease provide a config file using the --config flag.')
        print(f'{f.cgray}Example: python3 -m mhubio.run --config /app/models/{f.funderline}$model_name{f.fnormal+f.cgray}/config/config.yml{f.cend}\n')

        if interactive:
            config_file = interactive_routine()
            
            if config_file is None:
                print('Aborted.')
                sys.exit(0)

        else:
            configurations = scan_configurations()
            print_configurations(configurations)
            sys.exit(0)
    else:
        config_file_argv_index = sys.argv.index('--config')
        if len(sys.argv) > config_file_argv_index + 1:
            config_file = sys.argv[config_file_argv_index + 1]

    # ensure that if a config file is provided, it exists
    if config_file is not None and not os.path.isfile(config_file):
        #print(f"{f.cyan}Warning:{f.cend} The config file {f.fitalics}{config_file}{f.fnormal} does not exist.")
        print(f'{f.cyellow+f.fbold} Warning:{f.fnormal+f.cyellow} The provided config file {f.fitalics}{config_file}{f.fnormal+f.cyellow} does not exist.{f.cend}')
        sys.exit(0)
    
    # cleanup
    if '--cleanup' in sys.argv:
        cleanup()

    # run
    run(config_file)