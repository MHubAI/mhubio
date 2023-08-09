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
    'MhaConverter': 'mhubio.modules.convert.MhaConverter',
    'TiffConverter': 'mhubio.modules.convert.TiffConverter',
    'RTStructConverter': 'mhubio.modules.convert.RTStructConverter',

    'DataOrganizer': 'mhubio.modules.organizer.DataOrganizer',

    'JsonSegExporter': 'mhubio.modules.exporter.JsonSegExporter',
    'ReportExporter': 'mhubio.modules.exporter.ReportExporter',

    'DummyRunner': 'mhubio.modules.runner.DummyRunner',
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

def scan_configurations() -> List[Dict[str, str]]:
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
                    'name': os.path.splitext(config_file)[0],
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

def interactive_routine(configurations: List[Dict[str, str]]):
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

def get_config_path(configurations: List[Dict[str, str]]) -> Optional[str]:

    # if config file is specified esplicitly, we return it
    if '--config' in sys.argv:
        config_file_argv_index = sys.argv.index('--config')
        if len(sys.argv) > config_file_argv_index + 1:
            return sys.argv[config_file_argv_index + 1]

    # check if model is defined or there is only one model present
    models = list(set(c['model'] for c in configurations))
    model = None

    if len(models) == 1:
        model = models[0]

        # inform the user that there is just one model and it was selected automatically, so --model will be ignored. However, we'll clean up the commandline in the interactive routine so...
        if '--model' in sys.argv:
            print(f"{f.cyellow+f.fbold}Warning{f.cend+f.fnormal}: There is only one model present in this container, so the --model argument will be ignored. The model '{model}' will be used.")

    elif '--model' in sys.argv:
        model_argv_index = sys.argv.index('--model')
        if len(sys.argv) > model_argv_index + 1:
            model = sys.argv[model_argv_index + 1]
        
        # ensure that if --model is used, a mdoel name is specified
        if model is None:
            print(f"{f.chead+f.fbold}Error{f.cend+f.fnormal}: You need to specify a model name right after the --model argument.")
            sys.exit(0)

        # ensure that if a model is specified, it is present in the container
        if model is not None and not model in models:
            print(f"{f.chead+f.fbold}Error{f.cend+f.fnormal}: The specified model '{model}' was not found in this container.")
            sys.exit(0)
    
    else:
        print(f"{f.chead+f.fbold}Error{f.cend+f.fnormal}: Multiple models found but no model specified. Use --model $model_name to specify the model where we will search for workflows (configuration files).")
        print(f"Available models: {', '.join(models)}")
        sys.exit(0)
    

    # check if workflow is defined
    assert model is not None
    workflows = [c['name'] for c in configurations if c['model'] == model]
    workflow = None

    if '--workflow' in sys.argv:
        workflow_argv_index = sys.argv.index('--workflow')
        if len(sys.argv) > workflow_argv_index + 1:
            workflow = sys.argv[workflow_argv_index + 1]
            
        # ensure that if --workflow is used, a workflow name is specified
        if workflow is None:
            print(f"{f.chead+f.fbold}Error{f.cend+f.fnormal}: You need to specify a workflow name right after the --workflow argument.")
            sys.exit(0)

        # workflow 'config' and 'default' are used synonymously.
        # TODO: we could check if there are two workflows with either names present but we better forbid using 'config' as a name in the future and encourage the use of 'default' instead.

        if workflow == 'default' and 'config' in workflows:
            workflow = 'config'

        # ensure that if a workflow is specified, it is present in the container
        if workflow is not None and not workflow in workflows:
            print(f"{f.chead+f.fbold}Error{f.cend+f.fnormal}: The specified workflow '{workflow}' was not found in this container.")
            sys.exit(0)

        # build config path
        assert model is not None and workflow is not None
        return f'/app/models/{model}/config/{workflow}.yml'

    # return None if no configuration is found
    return None

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

    # start at step 
    # TODO: fh export per workflow -> sub-folder with wf name
    if '--start-at' in sys.argv:
        start_at = int(sys.argv[sys.argv.index('--start-at') + 1])

        if start_at <= 0:
            print(f'{f.cyellow+f.fbold} Warning:{f.fnormal+f.cyellow} The specified start-at index is smaller than 1. Just run the workflow without the --start-at flag instead.{f.cend}')
            return

        # chek if export available under /app/data/debug file_handler_{i}.yml 
        fhexp_path = f'/app/data/debug/file_handler_{start_at-1}.yml'
        if not os.path.exists(fhexp_path):
            print(f'{f.cyellow+f.fbold} Warning:{f.fnormal+f.cyellow} No export file found at {fhexp_path}. Please run the workflow from the beginning.{f.cend}')
            return
        
        # check if workflow is long enough
        if len(workflow) < start_at:
            print(f'{f.cyellow+f.fbold} Warning:{f.fnormal+f.cyellow} The specified start-at index is larger than the workflow length. Please run the workflow from the beginning.{f.cend}')
            return
        
        # remove all modules before start_at
        workflow = workflow[start_at:]

        # print new workflow
        print(f'\n{f.cyan+f.fbold} Workflow:{f.cend}')
        for i, (m, _) in enumerate(workflow):
            print(f'{f.cgray}  - {i+start_at}: {m}{f.cend}')

        # import file handler
        print(f'\n{f.chead} Importing file handler from {fhexp_path}{f.cend}')
        config.data.import_yml(fhexp_path)

        # print inital debug
        print(f'\n{f.cyan+f.fbold} Initial debug:{f.cend}')
        config.data.printInstancesOverview()

    # sanity check
    if not all([module[0] in import_paths for module in workflow]):
        print(f'{f.cyellow+f.fbold} Warning:{f.fnormal+f.cyellow} One or more modules in the execution chain are not available. You may use a custom run script insead.{f.cend}')
        for (m, _) in workflow:
            if m not in import_paths:
                print(f'{f.cgray}  - {m}{f.cend}')
        return 

    # sequential execution
    for i, (class_name, model_config) in enumerate(workflow):

        mimport = importlib.import_module(import_paths[class_name])
        module: Type[Module] = getattr(mimport, class_name)
        kwargs = initialization_arguments[class_name] if class_name in initialization_arguments else {}

        module(
            config = config, 
            local_config = model_config, 
            **kwargs
        ).execute()

        # export file handler yml 
        if '--export-file-handler' in sys.argv:
            if not os.path.exists('/app/data/debug'):
                os.makedirs('/app/data/debug')
            config.data.export_yml(f'/app/data/debug/file_handler_{i}.yml')

if __name__ == '__main__':

    # interactive mode?
    interactive = '--non-interactive' not in sys.argv

    # scan configurations
    configurations = scan_configurations()

    # get config file (if provided by one of the supported methods)
    config_file = get_config_path(configurations)

    # check if a config file is provided via the --config argument
    if config_file is None:

        print('\nPlease specify a workflow using the --workflow flag (also specify the model using the --model flag if multiple models are present in the container) or provide a config file using the --config flag.')
        print(f'{f.cgray}Example: python3 -m mhubio.run --config /app/models/{f.funderline}$model_name{f.fnormal+f.cgray}/config/config.yml{f.cend}\n')

        if interactive:
            config_file = interactive_routine(configurations)
            
            if config_file is None:
                print('Aborted.')
                sys.exit(0)

        else:
            print_configurations(configurations)
            sys.exit(0)

    # ensure that if a config file is provided, it exists
    if config_file is not None and not os.path.isfile(config_file):
        print(f'{f.cyellow+f.fbold} Warning:{f.fnormal+f.cyellow} The provided config file {f.fitalics}{config_file}{f.fnormal+f.cyellow} does not exist.{f.cend}')
        sys.exit(0)

    # NOTE: to this point, config_file may still be unspecified (None) 
    #       allowing the user plans to run using the minimal default config.
    
    # cleanup
    if '--cleanup' in sys.argv and not '--start-at' in sys.argv:
        cleanup()

    # run
    run(config_file)