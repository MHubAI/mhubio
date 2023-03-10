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
import os

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