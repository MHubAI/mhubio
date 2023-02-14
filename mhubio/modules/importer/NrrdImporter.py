import os

from mhubio.Config import UnsortedInstance, InstanceData, DataType, FileType, CT
from mhubio.modules.importer.DataImporter import DataImporter

class NrrdImporter(DataImporter):

    def task(self) -> None:
        # input nrrd file name
        input_dir = self.c['input_dir']
        input_file_name = self.c['input_file_name']

        # add input nrrd file
        self.setBasePath(input_dir)
        self.addNrrdCT(input_file_name, ref=None)

        # let the base module take over from here
        super().task()