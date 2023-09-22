
from typing import TypeVar, Callable, Any, Optional, Union, Type, List, Dict
from typing_extensions import ParamSpec, Concatenate, get_origin
from mhubio.core import Module, Instance, InstanceData, InstanceDataCollection, DataType, Meta, DataTypeQuery
from mhubio.core.RunnerOutput import RunnerOutput
from inspect import signature
import os, traceback
from .Logger import ConsoleCapture

# typing aliases and placeholders
T = TypeVar('T', bound=Module)
V = TypeVar('V')
W = TypeVar('W')
A = Union[V, Callable[[Module], V]]
Aopt = Optional[Union[V, Callable[[Module], V]]]
P = ParamSpec("P")
OT = TypeVar('OT', bound=RunnerOutput)

# custom exceptions
class IOError(Exception):
    pass

# helper functions
def check_signature(func: Callable[..., Any], sig: Dict[str, Type]):
    if not hasattr(func, '_mhubio_ofunc'):
       return

    for key, value in sig.items():
        ofunc_sig = signature(func._mhubio_ofunc)
        if not key in ofunc_sig.parameters:
            raise IOError(f"IO ErrorFunction '{func._mhubio_ofunc.__name__}' does not have parameter '{key}'.")
        if not ofunc_sig.parameters[key].annotation == value:
            raise IOError(f"Parameter '{key}' of function '{func._mhubio_ofunc.__name__}' must be of type '{value}' but is of type '{ofunc_sig.parameters[key].annotation}' instead.")

def resolve_dtq(self: Module, func: Callable[..., Any], name: str, dtype: Aopt[str] = None) -> str:
    if dtype is None:
        assert hasattr(self, '_mhubio_configinput_' + name), \
            f"@IO.Input wrapper on Method {self.__class__.__name__}.{(func._mhubio_ofunc if hasattr(func, '_mhubio_ofunc') else func).__name__}(..) has no dtype set and no matching @IO.ConfigInput wrapper with name '{name}' found on Class {self.__class__.__name__}."
        return getattr(self, '_mhubio_configinput_' + name)()
    elif callable(dtype):
        return dtype(self) 
    else:
        return dtype

# factory tools
class F:
    @staticmethod
    def list(func: Callable[[Any], V]) -> Callable[[List[Any]], List[V]]:
        def list_factory(l: List[Any]) -> List[V]:
            return [func(x) for x in l]
        return list_factory

# IO
class IO:

    # factory tools
    F = F()

    # dy
    @staticmethod
    def C(key: str, type: Optional[Type[V]] = Any) -> Callable[[Module], V]:
        def c(self: Module) -> V:
            return getattr(self, key)
        return c
    
    @staticmethod
    def CP(*fns: Union[str, Callable[[Module], Any]]) -> Callable[[Module], str]:
        def c(self: Module) -> str:
            return ''.join(str(fn(self) if callable(fn) else fn for fn in fns))
        return c

    @staticmethod
    def IF(key: str, if_true: V, if_false: V) -> Callable[[Module], V]:
        def callable(self: Module) -> V:
            return if_true if getattr(self, key) else if_false
        return callable

    @classmethod
    def Config(cls: Type['IO'], name: str, type: Type[V], default: W, factory: Callable[[W], V] = lambda x: x, the: Optional[str] = None) -> Callable[[Type[T]], Type[T]]:
        # wrapper
        def wrapper(dcls: Type[T]) -> Type[T]:

            # assert the class has the specified attibute
            if not name in dcls.__annotations__: 
                raise IOError(f"Class does not have attribute {name}")
            
            if dcls.__annotations__[name] != type: 
                raise IOError(f"Configurable attribute '{name}' must be of type {type}")
            
            if default is not None and not isinstance(factory(default), get_origin(type) or type): 
                raise IOError(f"Default value of '{name}' must be of type {type}")

            # getter: class attribute > config > default
            def getAttr(self: T, attr_name=name) -> V:
                clsattr = "_mhubio_configurable__" + attr_name
                if not hasattr(self, clsattr):
                    #f = factory or type.from_config if isinstance(type, Registrable) else lambda x: x
                    setattr(self, clsattr, factory(self.getConfiguration(attr_name, default)))
                return getattr(self, clsattr)

            # setter
            def setAttr(self: T, value: V, attr_name=name):
                if not isinstance(value, get_origin(type) or type):
                    raise IOError(f"Configurable attribute must be of type {type}")
                setattr(self, "_mhubio_configurable__" + attr_name, value)

            prop: property = property(getAttr, setAttr)
            setattr(dcls, name, prop)

            # return class with updated getter and setter for property
            return dcls
        
        return wrapper

    @classmethod
    def ConfigInput(cls: Type['IO'], name: str, default: str, class_attribute: bool = False, the: Optional[str] = None) -> Callable[[Type[T]], Type[T]]:
        
        # wrapper
        def wrapper(dcls: Type[T]) -> Type[T]:

            # assert the class has the specified attibute
            if class_attribute and not name in dcls.__annotations__: 
                raise IOError(f"Class does not have attribute {name}")
            
            if class_attribute and dcls.__annotations__[name] != DataTypeQuery: 
                raise IOError("Configurable attribute must be of type DataTypeQuery")
            
            if default is not None and not isinstance(default, str): 
                raise IOError("Default value must be of type str")

            # getter: class attribute > config > default
            def getAttr(self: T, attr_name=name) -> DataTypeQuery:
                clsattr = "_mhubio_configurable__" + attr_name
                
                if not hasattr(self, clsattr):
                    setattr(self, clsattr, DataTypeQuery(self.getConfiguration(attr_name, default)))
                return getattr(self, clsattr)

            # setter
            def setAttr(self: T, value: DataTypeQuery, attr_name=name):
                if not isinstance(value, get_origin(type) or type):
                    raise IOError(f"Configurable attribute must be of type {type}")
                setattr(self, "_mhubio_configurable__" + attr_name, value)

            if class_attribute:
                prop: property = property(getAttr, setAttr)
                setattr(dcls, name, prop)

            # getter for @IO.Input 
            #   we won't reuse prop here to minimize confusion, also it's better to have prop optional 
            #   as it's barely needed and mhubio is less used in python scripts anyhow
            setattr(dcls, "_mhubio_configinput_" + name, getAttr)

            # return class with updated getter and setter for property
            return dcls
        
        return wrapper
    

    @staticmethod
    def Instance(include_global_instance: bool = False) -> Callable[[Callable[Concatenate[T, Instance, P], None]], Callable[[T], None]]:
        def decorator(func: Callable[Concatenate[T, Instance, P], None]) -> Callable[[T], None]:
            check_signature(func, {'instance': Instance})
            def wrapper(self: T, *args: P.args, **kwargs: P.kwargs) -> None:
                
                # global instacne (exclude from instace logging, log on module level)
                if include_global_instance:
                    try:
                        with ConsoleCapture(self.config.logger):
                            func(self, self.config.data.globalInstance, *args, **kwargs)
                    except Exception as e:
                        self.log(f"ERROR: {self.__class__.__name__} failed processing instance {str(self.config.data.globalInstance)}: {str(e)} in {traceback.format_exc()}", level='ERROR')

                # iterate through all instances
                for instance in self.config.data.instances:
                    #if instance.attr['status'] == 'failed' and not include_failed_instances:
                    #    continue
                    try:

                        # start instance logging if MLog is set-up
                        if self.config.logger is not None:
                            self.config.logger.startInstance(instance)

                        # call modules (wrapped) task function for instance
                        with ConsoleCapture(self.config.logger) as output:
                            func(self, instance, *args, **kwargs)

                    except Exception as e:
                        # TODO: add logging, generate final report
                        self.log(f"ERROR: {self.__class__.__name__} failed processing instance {str(instance)}: {str(e)} in {traceback.format_exc()}", level='ERROR')

                        # set instance status attribute 
                        # instance.attr['status'] = 'failed' (-> for this add 'status: ok' to default instance.attr)
                   
                    finally:
                        # finish instance logging if MLog is set-up 
                        if self.config.logger is not None:
                            self.config.logger.finishInstance(instance)

            #
            wrapper._mhubio_ofunc = func._mhubio_ofunc if hasattr(func, '_mhubio_ofunc') else func          

            return wrapper
        return decorator
    
    @staticmethod
    def Input(name: str, dtype: Aopt[str] = None, the: Optional[str] = None) -> Callable[[Callable[Concatenate[T, 'Instance', P], None]], Callable[[T, 'Instance'], None]]:
        def decorator(func: Callable[Concatenate[T, Instance, P], None]) -> Callable[[T, Instance], None]:
            check_signature(func, {name: InstanceData})
            def wrapper(self: T, instance: Instance, *args: P.args, **kwargs: P.kwargs) -> None:
                _dtype = resolve_dtq(self, func, name, dtype)
                kwargs[name] = instance.data.first(_dtype)
                func(self, instance, *args, **kwargs)
            wrapper._mhubio_ofunc = func._mhubio_ofunc if hasattr(func, '_mhubio_ofunc') else func   
            return wrapper
        return decorator

    @staticmethod
    def Inputs(name: str, dtype: Aopt[str] = None, the: Optional[str] = None) -> Callable[[Callable[Concatenate[T, 'Instance', P], None]], Callable[[T, 'Instance'], None]]:
        def decorator(func: Callable[Concatenate[T, Instance, P], None]) -> Callable[[T, Instance], None]:
            check_signature(func, {name: InstanceDataCollection})
            def wrapper(self: T, instance: Instance, *args: P.args, **kwargs: P.kwargs) -> None:
                _dtype = resolve_dtq(self, func, name, dtype)
                kwargs[name] = instance.data.filter(_dtype)
                func(self, instance, *args, **kwargs)
            wrapper._mhubio_ofunc = func._mhubio_ofunc if hasattr(func, '_mhubio_ofunc') else func   
            return wrapper
        return decorator
    
    @staticmethod
    def OutputData(name: str, type: Type[OT], data: Optional[str] = None, the: Optional[str] = None) -> Callable[[Callable[Concatenate[T, 'Instance', P], None]], Callable[[T, 'Instance'], None]]:
        if the is not None: 
            type.description = the

        if not hasattr(type, 'description') or not type.description:
            raise IOError(f"OutputData {name} must have a description.")

        def decorator(func: Callable[Concatenate[T, Instance, P], None]) -> Callable[[T, Instance], None]:
            
            check_signature(func, {name: type})                
            
            def wrapper(self: T, instance: Instance, *args: P.args, **kwargs: P.kwargs) -> None:

                # ref data
                ref_data = kwargs[data] if data is not None else None
                assert isinstance(ref_data, InstanceData) or ref_data is None

                # create instance of output class
                output = type()

                # copy meta data from ref data if any
                if ref_data is not None and ref_data.type.meta:
                    output.meta = ref_data.type.meta + (output.meta or Meta())

                # call wrapped function
                kwargs[name] = output
                func(self, instance, *args, **kwargs)

                # assign
                instance.setData(output)
                
            wrapper._mhubio_ofunc = func._mhubio_ofunc if hasattr(func, '_mhubio_ofunc') else func   
            return wrapper
        return decorator

    @staticmethod
    def Output(name: str, path: A[str], dtype: A[str], data: Optional[str] = None, bundle: Optional[A[str]] = None, auto_increment: bool = False, in_signature: bool = True, the: Optional[str] = None) -> Callable[[Callable[Concatenate[T, 'Instance', P], None]], Callable[[T, 'Instance'], None]]:
        def decorator(func: Callable[Concatenate[T, Instance, P], None]) -> Callable[[T, Instance], None]:
            
            if in_signature:
                check_signature(func, {name: InstanceData})
                
            def wrapper(self: T, instance: Instance, *args: P.args, **kwargs: P.kwargs) -> None:

                # ref data
                ref_data = kwargs[data] if data is not None else None
                assert isinstance(ref_data, InstanceData) or ref_data is None

                # create output data
                _dtype = dtype(self) if callable(dtype) else dtype
                _path = path(self) if callable(path) else path
                _bundle = bundle(self) if callable(bundle) else bundle if bundle is not None else None

                # copy meta data from ref data if any
                ref_data_meta = ref_data.type.meta if ref_data is not None else Meta()
                out_data_type = DataType.fromString(_dtype)
                out_data_type.meta = ref_data_meta + out_data_type.meta

                # create bundle
                ref_bundle = (ref_data or instance).getDataBundle(_bundle) if _bundle is not None else None

                # create instance data
                out_data = InstanceData(path=_path, type=out_data_type, instance=instance, bundle=ref_bundle, data=ref_data, auto_increment=auto_increment)

                # make sure directory chain exist
                out_data.dc.makedirs()

                # call wrapped function
                kwargs[name] = out_data
                func(self, instance, *args, **kwargs)

                # verify output data was created at expected path
                if os.path.exists(out_data.abspath):
                    out_data.confirm()
                
            wrapper._mhubio_ofunc = func._mhubio_ofunc if hasattr(func, '_mhubio_ofunc') else func   
            return wrapper
        return decorator

    @staticmethod
    def Outputs(name: str, path: A[str], dtype: A[str], data: Optional[str] = None, bundle: Optional[A[str]] = None, wrapper: Optional[A[str]] = None, auto_increment: bool = False, in_signature: bool = True, the: Optional[str] = None) -> Callable[[Callable[Concatenate[T, 'Instance', P], None]], Callable[[T, 'Instance'], None]]:
        
        if bundle and wrapper:
            raise IOError("Cannot specify both bundle and wrapper")

        def decorator(func: Callable[Concatenate[T, Instance, P], None]) -> Callable[[T, Instance], None]:
            
            if in_signature: 
                check_signature(func, {name: InstanceDataCollection})
            
            def wfunc(self: T, instance: Instance, *args: P.args, **kwargs: P.kwargs) -> None:

                # ref data
                ref_data = kwargs[data] if data is not None else None
                assert isinstance(ref_data, InstanceDataCollection) 

                # create output data
                _dtype = dtype(self) if callable(dtype) else dtype
                _path = path(self) if callable(path) else path
                _bundle = bundle(self) if callable(bundle) else bundle if bundle is not None else None
                _wrapper = wrapper(self) if callable(wrapper) else wrapper if wrapper is not None else None

                idc = InstanceDataCollection()
                for _one_data in ref_data:

                    # NOTE: bundle and wrapper both create a bundle on each input data that is then passed to the output data constructor, effectively creating a new bundle for each output data. While wrapper creates a bundle based on the input data name, bundle creates a bundle based on the specified name. If all input data share the same bundle or have no bundle set, bundle will create different objects that all point to the same path, hence they effectively share that bundle.

                    # create bundle (if specified)
                    ref_bundle = _one_data.getDataBundle(_bundle) if _bundle is not None else None

                    # create wrapping bundle (if specified)
                    if _wrapper is not None and _wrapper == '*name':
                        ref_bundle_name = os.path.basename(_one_data.abspath).replace('.', '_')
                        ref_bundle = _one_data.getDataBundle(ref_bundle_name)

                    # create bundle folder if required
                    if ref_bundle and not os.path.exists(ref_bundle.abspath):
                        os.makedirs(ref_bundle.abspath)

                    # news idea, use dynamic paths (similar to organizer)
                    _one_data_bn = os.path.basename(_one_data.abspath)
                    _one_data_path = _path.replace('[basename]', _one_data_bn)
                    _one_data_path = _one_data_path.replace('[filename]', _one_data_bn.split('.', 1)[0])
                    _one_data_path = _one_data_path.replace('[filext]', _one_data_bn.split('.', 1)[1] if _one_data_bn.count('.') > 0 else '')

                    # copy meta data from ref data if any
                    out_data_type = DataType.fromString(_dtype)
                    out_data_type.meta = _one_data.type.meta + out_data_type.meta

                    # create instance data and add to collection
                    out_data = InstanceData(path=_one_data_path, type=out_data_type, instance=instance, bundle=ref_bundle, data=_one_data, auto_increment=auto_increment)
                    idc.add(out_data)

                # call wrapped function
                kwargs[name] = idc
                func(self, instance, *args, **kwargs)

                # verify output data was created at expected path
                for out_data in idc:
                    if os.path.exists(out_data.abspath):
                        out_data.confirm()
                
            wfunc._mhubio_ofunc = func._mhubio_ofunc if hasattr(func, '_mhubio_ofunc') else func   
            return wfunc
        return decorator

    # NOTE: only works on single input. We might create a universal decorator that can detect wheather there is a single input data or a collection of inputs. 
    #       But for now I outsource the bundle creation to the output data creation which seems reasonable and simplifies the interface.

    # NOTE: 2: In the scenario, where a model generates n files with known names and the @IO.Input operators are set to match these names, it might be easiest to create a bundle, then let the model output it's files into that bundle and define the @IO.Input operators linked to that bundle. The confirmation check then ensures wheather the files were found or not. This seems better than a copy instruction for those files (preventing hardcoding model output file names twice). Could this work for multiple inputs too? Check this with the Platipy use case.
    @staticmethod
    def Bundle(name: str, path: Optional[A[str]] = None, data: Optional[str] = None, the: Optional[str] = None) -> Callable[[Callable[Concatenate[T, 'Instance', P], None]], Callable[[T, 'Instance'], Any]]:
        #raise IOError("Bundle decorator not yet supported")
        def decorator(func: Callable[Concatenate[T, 'Instance', P], None]) -> Callable[[T, 'Instance'], None]:
            def wrapper(self: T, instance: Instance, *args: P.args, **kwargs: P.kwargs) -> None: 
                _path = path(self) if callable(path) else path               
                ref_data = kwargs[data] if data is not None else None
                assert ref_data is None or isinstance(ref_data, InstanceData)
                kwargs[name] = (ref_data or instance).getDataBundle(_path or name)
                return func(self, instance, *args, **kwargs)
            wrapper._mhubio_ofunc = func._mhubio_ofunc if hasattr(func, '_mhubio_ofunc') else func 
            return wrapper
        return decorator 
    