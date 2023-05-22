"""
-------------------------------------------------
DEPRECATED MODULE - DO NOT USE
MHub - Data Sorter Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

import os
import subprocess
import shutil

from mhubio.core import Config, UnsortedInstance, SortedInstance, InstanceData, DataType, FileType, CT, DirectoryChain
from mhubio.modules.importer.DataImporter import DataImporter

class DataSorter(DataImporter):
    """
    Sort Module.
    Organize patient data in a unique folder structure.
    For now, the static schema is: %SeriesInstanceUID/dicom/%SOPInstanceUID.dcm
    """

    def __init__(self, config: Config):
        super().__init__(config)

        # deprecation warning
        print("----------------------------------------------------------------------------")
        print("Deprecation Warning - importer.DataSorter initialized")
        print("UnsortedInstanceImporter + DataSorter are replaced by the new DicomImporter.")
        print("----------------------------------------------------------------------------")

        # get directory chain based on the data handler and the configured base dir
        # NOTE: setting `base_dir` to an absolute path (starting with /) will override the data handler prefix path and make it an entrypoint instead. 
        self.dc = DirectoryChain(path=self.c['base_dir'], parent=self.config.data.dc)
        
        # bypass mode
        self.bypass: bool = bool(self.c['bypass']) if 'bypass' in self.c else False

    # override instance generator 
    def _generateInstance(self, path: str) -> SortedInstance:
        return SortedInstance(path)

    def sort(self) -> None:    

        # deprecation warning
        print("----------------------------------------------------------------------------")
        print("Deprecation Warning - importer.DataSorter used")
        print("UnsortedInstanceImporter + DataSorter are replaced by the new DicomImporter.")
        print("----------------------------------------------------------------------------")
        
        # get input data
        instances = self.config.data.instances
        assert len(instances) == 1, "Error: too many or too less instances. Sorter expxts a single, unsorted instance."
        instance = instances[0]
        assert type(instance) == UnsortedInstance, "Error: instance must be unsorted."

        # print schema
        # TODO: config and integration of schema into folder struction ablation
        #schema = str(self.c['base_dir']) + "/" + str(self.c['structure'])
        schema = os.path.join(self.dc.abspath, self.c['structure'])
        self.v("sorting schema:",  schema)

        # create output folder if required
        if not os.path.isdir(self.dc.abspath):
            os.makedirs(self.dc.abspath)

        # compose command
        bash_command = [
            "dicomsort", 
            "-k", "-u",
            instance.abspath, 
            schema
        ]

        # TODO: remove
        self.v(">> run: ", " ".join(bash_command))

        _ = subprocess.run(bash_command, check=True, text=True)

        # iterate all created files and add them to teh data importer
        for sid in self.getSeriesIDs():
            self.addDicomCT(path="dicom", ref=sid)
            self.setAttribute('ref', sid, ref=sid)
            self.setAttribute('SeriesID', sid, ref=sid)
    
    def getSeriesIDs(self):
        return os.listdir(self.dc.abspath)

    def dry(self):
        # dry sort (linking data only without sorting)

        # get input data
        instances = self.config.data.instances
        assert len(instances) == 1, "Error: too many or too less instances. Sorter expxts a single, unsorted instance."
        instance = instances[0]
        assert type(instance) == UnsortedInstance, "Error: instance must be unsorted."

        # check input folder
        hasOnlyDicomFiles: bool = True
        hasOnlyFolders: bool = True
        for d in os.listdir(instance.abspath):
            if not os.path.isfile(os.path.join(instance.abspath, d)) or not d.endswith(".dcm"):
                hasOnlyDicomFiles = False
            if not os.path.isdir(os.path.join(instance.abspath, d)):
                hasOnlyFolders = False

        # error
        if hasOnlyDicomFiles == hasOnlyFolders:
            raise ValueError("Error: input directory contains both dicom files and folders. Cannot determine if this is a single series or multiple series.")

        # create output folder if required
        if not os.path.isdir(self.dc.abspath):
            os.makedirs(self.dc.abspath)



        # Case 1: input directory contains only dicom files and will be imported as a single series
        if hasOnlyDicomFiles:

            # create dicom folder
            os.mkdir(os.path.join(self.dc.abspath, "dicom"))

            # copy data
            for f in os.listdir(instance.abspath):
                shutil.copyfile(os.path.join(instance.abspath, f), os.path.join(self.dc.abspath, "dicom", f))

            # add data
            # TODO: how to set attributes (SeriesID, ref, ...)
            self.addDicomCT(path="dicom", ref=None)

        # Case 2: input directory contains multiple series and will be imported as multiple series
        if hasOnlyFolders:

            # iterate folders
            for d in os.listdir(instance.abspath):
                
                # make folder 
                os.makedirs(os.path.join(self.dc.abspath, d), exist_ok=True)

                # copy folder
                shutil.copytree(os.path.join(instance.abspath, d), os.path.join(self.dc.abspath, d, "dicom"))

                # add data
                # TODO: (how to) set SeriesID attribute? 
                self.addDicomCT(path="dicom", ref=d)
                self.setAttribute('ref', d, ref=d)

    def task(self) -> None:

        # TODO: self.c['base_dir'] will be used here in the future but currrently is /app/data/sorted, whereas the actual instance base is "sorted" because "/app/data" is the data handler base path. Add a global rel/abs path resolving mechanism to handle these kinds safely. Also add this (and all actions) to a describing log file so everybody can see what's going on in terms of data handling!
        # NOTE: Thinking about this, I will put the current dynamic resolving folder structure approach under revision. Although it looks nice (and will make debugging / inspection a ton easyer), there is no neeed to have a well defined folder structure hidden in the docker if we keep track of all files anyways, especially since we always could export the files (as with the organizer module). However, the current approach makes the pipeline more compatible with (our)traditional folder structure. Thinking about transparency, the jupyter notebooks might benefit from a well-defined folder structure! SO pro's and con's.
        self.setBasePath(self.dc.abspath)

        # run dicomsort
        if not self.bypass:
            self.sort() 
        else:
            self.dry()

        # let the data importer base module care for the rest!
        super().task()