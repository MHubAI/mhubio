"""
-------------------------------------------------
DEPRECATED MODULE - DO NOT USE
MHub - Special NRRD importer for 3D Slicer plugin
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from mhubio.core import Config
from mhubio.modules.importer.DataImporter import DataImporter

class NrrdImporter(DataImporter):

    def __init__(self, config: Config, **kwargs) -> None:
        super().__init__(config, **kwargs)

        # deprecation warning
        print("----------------------------------------------------------------------------")
        print("Deprecation Warning - importer.NrrdImporter initialized")
        print("NrrdImporter are replaced by the new universal FileStructureImporter.")
        print("----------------------------------------------------------------------------")

    def task(self) -> None:
        # input nrrd file name
        input_dir = self.c['input_dir']
        input_file_name = self.c['input_file_name']

        # add input nrrd file
        self.setBasePath(input_dir)
        self.addNrrdCT(input_file_name, ref=None)

        # let the base module take over from here
        super().task()