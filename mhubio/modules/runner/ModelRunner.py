"""
-------------------------------------------------
MHub - Model Runner Base Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import List
import os, subprocess
from mhubio.core import Module, Instance


class ModelRunner(Module):

    # TODO: since the ModelRunner is always customized, we could consider adding an additional layer of support here. E.g. we could define the required data formats and then already pre-filter instances accordingly. Extending this further, we could even add pre-checks etc. However, it might be equally valid or even better for transparency to have all pre-checks and filtering steps present in the run.py script.
    
    # TODO: standardize "model" meta type and auto-set to all exported instance data

    def task(self) -> None:
        for instance in self.config.data.instances:
            try:
                self.runModel(instance)
            except Exception as e:
                # TODO: add global logging
                self.v("Error while running model for instance " + str(instance) + ": " + str(e))

    def runModel(self, instance: Instance) -> None:
        pass