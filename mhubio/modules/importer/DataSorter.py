"""
-------------------------------------------------
MHub - Data Sorter Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

import os
import subprocess

from mhubio.Config import Module, UnsortedInstance, SortedInstance, InstanceData, DataType, FileType, CT
from mhubio.modules.importer.DataImporter import DataImporter

class DataSorter(DataImporter):
    """
    Sort Module.
    Organize patient data in a unique folder structure.
    For now, the static schema is: %SeriesInstanceUID/dicom/%SOPInstanceUID.dcm
    """

    # override instance generator 
    def _generateInstance(self, path: str) -> SortedInstance:
        return SortedInstance(path)

    def sort(self) -> None:       
        
        # get input data
        instances = self.config.data.instances
        assert len(instances) == 1, "Error: too many or too less instances. Sorter expxts a single, unsorted instance."
        instance = instances[0]
        assert type(instance) == UnsortedInstance, "Error: instance must be unsorted."

        # print schema
        # TODO: config and integration of schema into folder struction ablation
        schema = str(self.c['base_dir']) + "/" + str(self.c['structure'])
        self.v("sorting schema:",  schema)

        # create output folder if required
        if not os.path.isdir(self.c['base_dir']):
            os.makedirs(self.c['base_dir'])

        # compose command
        bash_command = [
            "dicomsort", 
            "-k", "-u",
            str(instance.abspath), 
            schema
        ]

        # TODO: remove
        self.v(">> run: ", " ".join(bash_command))

        _ = subprocess.run(bash_command, check=True, text=True)

        # iterate all created files and add them to teh data importer
        for sid in self.getSeriesIDs():
            self.addDicomCT(path="dicom", ref=sid)
            self.setAttribute('SeriesID', sid, ref=sid)
    
    def getSeriesIDs(self):
        return os.listdir(self.c['base_dir'])

    def task(self) -> None:

        # TODO: self.c['base_dir'] will be used here in the future but currrently is /app/data/sorted, whereas the actual instance base is "sorted" because "/app/data" is the data handler base path. Add a global rel/abs path resolving mechanism to handle these kinds safely. Also add this (and all actions) to a describing log file so everybody can see what's going on in terms of data handling!
        # NOTE: Thinking about this, I will put the current dynamic resolving folder structure approach under revision. Although it looks nice (and will make debugging / inspection a ton easyer), there is no neeed to have a well defined folder structure hidden in the docker if we keep track of all files anyways, especially since we always could export the files (as with the organizer module). However, the current approach makes the pipeline more compatible with (our)traditional folder structure. Thinking about transparency, the jupyter notebooks might benefit from a well-defined folder structure! SO pro's and con's.
        self.setBasePath('sorted')

        # run dicomsort
        self.sort() 

        # let the data importer base module care for the rest!
        super().task()