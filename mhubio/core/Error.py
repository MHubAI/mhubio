"""
-------------------------------------------------
MHub - Error Classes
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

class MHubError(Exception):
    """Base class for exceptions in this module."""
    pass

class MHubMissingDataError(MHubError):
    pass