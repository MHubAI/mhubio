"""
-------------------------------------------------
DEPRECATED MODULE - DO NOT USE
MHub - Unsorted Dicom Importer Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import Optional

from mhubio.core import Config, UnsortedInstance
from mhubio.modules.importer.DataImporter import DataImporter

class UnsortedInstanceImporter(DataImporter):

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._parameter__input_dir: Optional[str] = None

        # deprecation warning
        print("----------------------------------------------------------------------------")
        print("Deprecation Warning - importer.UnsortedInstanceImporter initialized")
        print("UnsortedInstanceImporter + DataSorter are replaced by the new DicomImporter.")
        print("----------------------------------------------------------------------------")

    def setInputDir(self, input_dir: str) -> None:
        """Set the input directory (overwriting the config option).
        """
        self._parameter__input_dir = input_dir

    def task(self) -> None:
        # NOTE: bypassing the base importer, as we do not import instance data but instead a shadow instance (of type UnsortedInstance) 
        # that points to a folder containing all unsorted dicom data.
        
        # deprecation warning
        print("----------------------------------------------------------------------------")
        print("Deprecation Warning - importer.UnsortedInstanceImporter used")
        print("UnsortedInstanceImporter + DataSorter are replaced by the new DicomImporter.")
        print("----------------------------------------------------------------------------")

        # get input dir from config or parameter
        if self._parameter__input_dir is not None:
            input_dir = self._parameter__input_dir
        elif 'input_dir' in self.c and self.c['input_dir']:
            input_dir = self.c['input_dir']
        else:
            raise ValueError('No input directory provided to the unsorted data importer module. Set the input directory with all dicom files either using the configuration file or manually set the input directory via the setInputMethod in your run script.') 
        
        # add unsorted instance
        self.config.data.instances = [
            UnsortedInstance(input_dir)
        ]  