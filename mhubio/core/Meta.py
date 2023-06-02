"""
-------------------------------------------------
MHub - Meta class for mhubio instance data
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (27.02.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""
from typing import Union, Optional, Dict, List, Tuple

class Meta:

    #def __init__(self, key: Optional[str] = None, value: Optional[str] = None) -> None:
    #    self.mdict: Dict[str, str] = {key: value} if key and value else {}

    def __init__(self, **kwargs: str) -> None:
        self.mdict: Dict[str, str] = kwargs if kwargs else {}

    def ext(self, meta: Union[Dict[str, str], List['Meta'], 'Meta']) -> 'Meta':
        if isinstance(meta, dict):
            self.mdict = {**self.mdict, **meta}
        elif isinstance(meta, list) and all([isinstance(m, Meta) for m in meta]):
            for m in meta:
                self.mdict = {**self.mdict, **m.mdict}
        elif isinstance(meta, Meta):
            self.mdict = {**self.mdict, **meta.mdict}
        else:
            raise ValueError("Malformed metadata passed to DataType.")
        return self

    def keys(self) -> List[str]:
        return list(self.mdict.keys())

    def items(self) -> List[Tuple[str, str]]:
        return [(k, v) for k, v in self.mdict.items()]
    
    def values(self) -> List[str]:
        return list(self.mdict.values())

    # +
    def __add__(self, o: Union[Dict[str, str], List['Meta'], 'Meta']) -> 'Meta':
        return Meta().ext(self).ext(o)

    # -
    def __sub__(self, rks: List[str]) -> 'Meta':
        assert isinstance(rks, list) and all([isinstance(k, str) for k in rks])
        return Meta().ext({k: v for k, v in self.items() if not k in rks})

    # =
    def __eq__(self, o: Union[Dict[str, str], 'Meta']) -> bool:
        return self.mdict == (o.mdict if isinstance(o, Meta) else o)

    # in
    def __contains__(self, ks: Union[str, List[str]]) -> bool:
        assert isinstance(ks, str) or isinstance(ks, list) and all([isinstance(k, str) for k in ks])
        return ks in self.mdict if isinstance(ks, str) else all([k in self.mdict for k in ks])

    # <=
    # "less" is defined as "less general" (or more specific) since it targets a smaller subset of all possible combinations
    def __le__(self, o: Union[Dict[str, str], 'Meta']) -> bool:
        omdict = (o.mdict if isinstance(o, Meta) else o)
        assert isinstance(omdict, dict)
        for k, v in omdict.items():
            if v == '*':
                if k not in self.mdict:
                    return False
            elif self[k].lower() != v.lower():
                return False
        return True

    # []
    def __getitem__(self, key: str) -> str:
        return self.getValue(key)
    
    def getValue(self, key: str, default: str = "") -> str:
        assert isinstance(key, str)
        return self.mdict[key] if key in self.mdict else default

    def __str__(self) -> str:
        return ":".join(["%s=%s"%(k, v) for k, v in self.mdict.items()])

    def __len__(self) -> int:
        return len(self.mdict)

    def __bool__(self) -> bool:
        return len(self) > 0
    
    #def __dict__(self):
    #    return self.mdict
    def to_dict(self):
        return self.mdict