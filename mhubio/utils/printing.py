"""
-------------------------------------------------
MHub - printing utilities
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from enum import Enum

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