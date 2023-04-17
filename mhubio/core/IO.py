
from typing import TypeVar, Callable, Any, Optional, Union, Type, List, Dict
from typing_extensions import ParamSpec, Concatenate, get_origin
from mhubio.core import Module, Instance, InstanceData, InstanceDataCollection, DataType, Meta
from inspect import signature
import os, traceback

# typing aliases and placeholders
T = TypeVar('T', bound='Module')
V = TypeVar('V')
W = TypeVar('W')
A = Union[V, Callable[[Module], V]]
P = ParamSpec("P")

# custom exceptions
class IOError(Exception):
    pass

# helper functions
def check_signature(func: Callable[..., Any], sig: Dict[str, type]):
    if not hasattr(func, '_mhubio_ofunc'):
       return

    for key, value in sig.items():
        ofunc_sig = signature(func._mhubio_ofunc)
        if not key in ofunc_sig.parameters:
            raise IOError(f"IO ErrorFunction '{func._mhubio_ofunc.__name__}' does not have parameter '{key}'.")
        if not ofunc_sig.parameters[key].annotation == value:
            raise IOError(f"Parameter '{key}' of function '{func._mhubio_ofunc.__name__}' must be of type '{value}' but is of type '{ofunc_sig.parameters[key].annotation}' instead.")

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
        def callable(self: Module) -> V:
            return getattr(self, key)
        return callable

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
                raise IOError(f"Configurable attribute must be of type {type}")
            
            if default is not None and not isinstance(factory(default), get_origin(type) or type): 
                raise IOError(f"Default value must be of type {type}")

            # getter: class attribute > config > default
            def getAttr(self: T, attr_name=name) -> V:
                clsattr = "_configurable__" + attr_name
                if not hasattr(self, clsattr):
                    #f = factory or type.from_config if isinstance(type, Registrable) else lambda x: x
                    setattr(self, clsattr, factory(self.getConfiguration(attr_name, default)))
                return getattr(self, clsattr)

            # setter
            def setAttr(self: T, value: V, attr_name=name):
                if not isinstance(value, get_origin(type) or type):
                    raise IOError(f"Configurable attribute must be of type {type}")
                setattr(self, "_configurable__" + attr_name, value)

            prop: property = property(getAttr, setAttr)
            setattr(dcls, name, prop)

            # return class with updated getter and setter for property
            return dcls
        
        return wrapper

    @staticmethod
    def Instance() -> Callable[[Callable[Concatenate[T, Instance, P], None]], Callable[[T], None]]:
        def decorator(func: Callable[Concatenate[T, Instance, P], None]) -> Callable[[T], None]:
            check_signature(func, {'instance': Instance})
            def wrapper(self: T, *args: P.args, **kwargs: P.kwargs) -> None:
                for instance in self.config.data.instances:
                    try:
                        func(self, instance, *args, **kwargs)    
                    except Exception as e:
                        # TODO: add logging, generate final report
                        self.v(f"ERROR: Instance {str(instance)} failed with error {str(e)} in {traceback.format_exc()}")
            wrapper._mhubio_ofunc = func._mhubio_ofunc if hasattr(func, '_mhubio_ofunc') else func          
            return wrapper
        return decorator
    
    @staticmethod
    def Input(name: str, dtype: A[str], the: Optional[str] = None) -> Callable[[Callable[Concatenate[T, 'Instance', P], None]], Callable[[T, 'Instance'], None]]:
        def decorator(func: Callable[Concatenate[T, Instance, P], None]) -> Callable[[T, Instance], None]:
            check_signature(func, {name: InstanceData})
            def wrapper(self: T, instance: Instance, *args: P.args, **kwargs: P.kwargs) -> None:
                _dtype = dtype(self) if callable(dtype) else dtype
                kwargs[name] = instance.data.first(_dtype)
                func(self, instance, *args, **kwargs)
            wrapper._mhubio_ofunc = func._mhubio_ofunc if hasattr(func, '_mhubio_ofunc') else func   
            return wrapper
        return decorator

    @staticmethod
    def Inputs(name: str, dtype: A[str], the: Optional[str] = None) -> Callable[[Callable[Concatenate[T, 'Instance', P], None]], Callable[[T, 'Instance'], None]]:
        def decorator(func: Callable[Concatenate[T, Instance, P], None]) -> Callable[[T, Instance], None]:
            check_signature(func, {name: InstanceDataCollection})
            def wrapper(self: T, instance: Instance, *args: P.args, **kwargs: P.kwargs) -> None:
                _dtype = dtype(self) if callable(dtype) else dtype
                kwargs[name] = instance.data.filter(_dtype)
                func(self, instance, *args, **kwargs)
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

                    # copy meta data from ref data if any
                    out_data_type = DataType.fromString(_dtype)
                    out_data_type.meta = _one_data.type.meta + out_data_type.meta

                    # create instance data and add to collection
                    out_data = InstanceData(path=_path, type=out_data_type, instance=instance, bundle=ref_bundle, data=_one_data, auto_increment=auto_increment)
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
    @staticmethod
    def Bundle(name: str, path: Optional[A[str]] = None, data: Optional[str] = None, the: Optional[str] = None) -> Callable[[Callable[Concatenate[T, 'Instance', P], None]], Callable[[T, 'Instance'], Any]]:
        raise IOError("Bundle decorator not yet supported")
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
    