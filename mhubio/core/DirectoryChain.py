"""
-------------------------------------------------
MHub - DirectoryChain base and interface class 
for context aware directory structures.
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (27.02.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import Optional
import os, re

class DirectoryChain:
    """Directory chain (DC) is a recursive data structure that represents a path chain. 
    DC helps implementing a hierarchical data structure by mapping folder structure to semantic context.
    Given a hierarchical chain like A > B > C > D. If data is added to C, A/B/C is considered the context.
    
    Each DC instance has a path set at instantiation. 
    The instance's absolute path following the hiorarchical structure is provided by the abspath property.

    Although the hierarchical structure should be maintained whenever feasable, it is possible to set an absoluter path at any point in the hierarchical chain, making the instance a so called entrypoint. This can be achieved by one of the folowing options: 
    - set an absolut path (starting with /) as the DC instance's path
    - set the instance's base (path will be prefixed with base set base to an empty string to use path directly) 
    - call the instance's `makeEntrypoint(enforceAbsolutePath: bool = True)` method. 

    If an instance is an entrypoint can be checked by calling the `isEntrypoint()` method.
    """

    # path: str
    # base: str 
    # abspath: str

    def __init__(self, path: str, base: Optional[str] = None, parent: Optional['DirectoryChain'] = None) -> None:
        self.path: str = path
        self.base: Optional[str] = base
        self.parent: Optional[DirectoryChain] = parent

    def setBase(self, base: Optional[str]) -> None:
        self.base = base

    def setParent(self, parent: Optional['DirectoryChain']) -> None:
        self.parent = parent

    def setPath(self, path: str) -> None:
        self.path = path

    def isEntrypoint(self) -> bool:
        return self.base is not None or self.path[:1] == os.sep

    def makeEntrypoint(self, enforceAbsolutePath: bool = True) -> None:
        if enforceAbsolutePath:
            self.setBase("/")
        else:
            self.setBase("")

    def makedirs(self, exist_ok: bool = True) -> None:

        # check if abspath resolves to a file or directory
        is_file = re.match(r'^.*[^\/]+\.[^\.]+$', self.abspath) is not None

        # sanity checks
        assert exist_ok or not os.path.exists(self.abspath) # path must not exist

        # get base directory
        base_dir = os.path.dirname(self.abspath) if is_file else self.abspath

        # create base directory
        os.makedirs(base_dir, exist_ok=True)

        # sanity check
        assert exist_ok or not is_file or not os.path.isfile(self.abspath) # file must not be created
        assert os.path.isdir(base_dir) # base directory must exist / have been created

    def asDict(self) -> dict:
        return {
            "path": self.path,
            "base": self.base,
            "parent": self.parent.asDict() if self.parent is not None else None
        }
    
    @classmethod
    def fromDict(cls, d: dict) -> 'DirectoryChain':
        return cls(d["path"], d["base"], cls.fromDict(d["parent"]) if d["parent"] is not None else None)

    @property
    def abspath(self) -> str:
        if self.base is not None:
            return os.path.join(self.base, self.path)
        elif self.parent is not None:
            return os.path.join(self.parent.abspath, self.path)
        else:
            return self.path


class DirectoryChainInterface:
    """Every class part of a hierarchical data structure dealing with representative data should inherit from this class.
    By inheriting from this class, the class will have a `dc` property that is an instance of DirectoryChain and an `abspath` property that is a shortcut `self.dc.abspath`.
    """

    def __init__(self, path: str, base: Optional[str] = None, parent: Optional['DirectoryChain'] = None) -> None:
        self.dc = DirectoryChain(path, base, parent)

    @property
    def abspath(self) -> str:
        return self.dc.abspath