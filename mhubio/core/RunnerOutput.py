from enum import Enum
from typing import Type, Any, List, Optional, Union, Dict
from .Meta import Meta

class RunnerOutputType(Enum):
    ValuePrediction = 'ValuePrediction'
    ClassPrediction = 'ClassPrediction'

class RunnerOutput(): # Outcome?

    name: str
    label: str
    description: str
    type: RunnerOutputType
    _meta: Optional[Meta]

    def __str__(self):
        return f"[O:{self.name}:{self.type}:{self.label}:{self.description}]"

    @property # use property for optional values assigned via decorator
    def meta(self) -> Optional[Meta]:
        if hasattr(self, '_meta'):
            return self._meta
        return None
    
    @meta.setter
    def meta(self, meta: Optional[Meta]):
        self._meta = meta

    # static decorator function that assigns meta
    @staticmethod
    def Meta(meta: Meta):
        def decorator(cls):
            cls.meta = meta
            return cls
        return decorator

    # static decorator function that assigns name
    @staticmethod
    def Name(name: str):
        def decorator(cls):
            cls.name = name
            return cls
        return decorator
    
    # static decorator function that assigns label
    @staticmethod
    def Label(label: str):
        def decorator(cls):
            cls.label = label
            return cls
        return decorator
    
    # static decorator function that assigns description
    @staticmethod
    def Description(description: str):
        def decorator(cls):
            cls.description = description
            return cls
        return decorator
    
class ValueOutput(RunnerOutput):

    dtype: Type
    _value: Optional[Any]

    def __init__(self):
        super().__init__()
        self.type = RunnerOutputType.ValuePrediction

    @property
    def value(self) -> Optional[Any]:
        assert self._value is None or isinstance(self._value, self.dtype), f"Value {self._value} is not of type {self.dtype}."
        return self._value
    
    @value.setter
    def value(self, value: Optional[Any]):
        assert value is None or isinstance(value, self.dtype), f"Value {value} is not of type {self.dtype}."
        self._value = value

    # static decorator function that assigns type
    @staticmethod
    def Type(dtype: Type):
        def decorator(cls):
            cls.dtype = dtype
            return cls
        return decorator
    
    def __str__(self):
        return super().__str__() + f"({self.value})"

class OutputClass():
    classID: Union[int, str]
    probability: Optional[float] = None
    label: str
    description: str

    def __init__(self, classID: Union[int, str], label: str, description: str):
        self.classID = classID
        self.label = label
        self.description = description

    def __str__(self):
        return f"[C:{self.classID}:{self.label}]({self.probability})"

class ClassOutput(RunnerOutput):

    classes: List[OutputClass]
    _classID: Optional[Union[str, int]]

    def __init__(self) -> None:
        super().__init__()
        self.type = RunnerOutputType.ClassPrediction

        # reverse classes list, so top most decorator has index 0
        if hasattr(self, 'classes') and isinstance(self.classes, list):
            self.classes.reverse() 

    @property
    def value(self) -> Optional[Union[str, int]]:
        return self._classID
    
    @value.setter
    def value(self, classID: Optional[Union[str, int]]):
        assert classID is None or classID in self, f"Class with ID {classID} not found."
        self._classID = classID

    @property
    def predictedClass(self) -> Optional[OutputClass]:
        return self[self.value] if self.value is not None else None

    def assign_probabilities(self, class_data: Union[List[float], Dict[Union[str, int], float]]):
        """ Assigns probabilities to classes.
        
            class_data can be either a list of probabilities in the order as classes are defined 
            or a dictionary with classIDs as keys and the probabilities as float values.

            Note: decorators are read from top to bottom. 
                We therefore reverse the classes list, 
                so the top most decorator has index 0.
        """
        if isinstance(class_data, dict):
            for classID, probability in class_data.items():
                self[classID].probability = probability
        elif isinstance(class_data, list):
            for i, probability in enumerate(class_data):
                self.classes[i].probability = probability

    # access classes by their classID
    def __getitem__(self, classID: Union[str, int]) -> OutputClass:
        for c in self.classes:
            if c.classID == classID:
                return c
        raise KeyError(f"Class with ID {classID} not found.")

    # in operator to check if classID is in classes
    def __contains__(self, classID: Union[str, int]) -> bool:
        return any(c.classID == classID for c in self.classes)

    def __str__(self):
        return super().__str__() + f"<{'|'.join(str(c) for c in self.classes)}>({str(self.predictedClass)})"

    # static decorator to define a output class
    @staticmethod
    def Class(classID: Union[int, str], label: str, the: str):
        def decorator(cls):
            if not hasattr(cls, 'classes'):
                cls.classes = []
            cls.classes.append(OutputClass(classID, label, the))
            return cls
        return decorator

