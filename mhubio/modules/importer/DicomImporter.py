"""
-------------------------------------------------
MHub - DICOM Importer Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

import os
import subprocess
import shutil

from enum import Enum
from mhubio.core import Config, Module, Instance, InstanceData, DataType, Meta, FileType, CT, DirectoryChain, IO
import pydicom

class InputDirStructure(Enum):
    """
    Input directory structure options.
    """
    FLAT = 1
    SERIES = 2
    UNKNOWN = 3

@IO.Config('source_dir', str, 'input_data', the="source input directory containing the (unsorted) dicom data")
@IO.Config('import_dir', str, 'sorted_data', the="output directory where the imported (sorted / organized) dicom data will be placed")
@IO.Config('sort_data', bool, True, the="flag to turn data sorting using dicomsort off if input data is sorted already")
@IO.Config('meta', dict, {'mod': '%Modality'}, the="meta data used for every imported instance")
class DicomImporter(Module):
    """
    Import dicom data into instances after optionally sorting them.
    For now, the static schema is: %SeriesInstanceUID/dicom/%SOPInstanceUID.dcm

    To override the metadata via a custom config, pass a json string dictionary:
     ... '--config:modules.DicomImporter.meta={"mod": "MR"}'
    """

    source_dir: str
    import_dir: str
    sort_data: bool
    structure: str = "%SeriesInstanceUID/dicom/%SOPInstanceUID.dcm"
    meta: dict

    def sort(self, input_dir, sorted_dir, schema) -> None:   

        # print schema
        self.v()
        self.v("sorting dicom data")
        self.v("> input dir:  ", input_dir)
        self.v("> output dir: ", sorted_dir)
        self.v("> schema:     ", schema)

        # create output folder if required
        if not os.path.isdir(sorted_dir):
            self.v("> creating output folder: ", sorted_dir)
            os.makedirs(sorted_dir)

        # compose command
        bash_command = [
            "dicomsort", 
            "-k", "-u",
            input_dir, 
            os.path.join(sorted_dir, schema)
        ]

        # TODO: remove
        self.v(">> run: ", " ".join(bash_command))
        self.subprocess(bash_command, text=True)

    def updateMeta(self, dicom_data: InstanceData) -> None:

        if not any(v.startswith('%') for v in dicom_data.type.meta.values()):
            return

        # pick first file
        dicom_file = os.listdir(dicom_data.abspath)[0]
        dicom_file_path = os.path.join(dicom_data.abspath, dicom_file)

        # load dicom meta data
        ds = pydicom.read_file(dicom_file_path)

        # update meta (lookup dicom placeholders starting with %)
        meta_update = {}
        for k, v in dicom_data.type.meta.items():
            if v.startswith('%'):
                dicom_field = v[1:]
                if hasattr(ds, dicom_field):
                    meta_update[k] = getattr(ds, dicom_field)
                else:
                    self.v(f">> dicom field not found: {dicom_field}")

        # update meta of the dicom data
        dicom_data.type.meta += meta_update

    def importSorted(self, sorted_dir: str) -> None:
        
        # collect created instances
        instances = []

        # iterate sorted data and generate a new instance with the dicom data 
        instances_n = len(os.listdir(sorted_dir))
        for i, sid in enumerate(os.listdir(sorted_dir)):
            self.v(f"> importing sorted instance ({i+1}/{instances_n}): ", sid)
            
            # create new instance
            instance = Instance(os.path.join(sorted_dir, sid))
            instance.attr['sid'] = sid
            instances.append(instance)

            # create dicom data
            dicom_data_meta = self.meta.copy()
            dicom_data_type = DataType(FileType.DICOM, dicom_data_meta)
            dicom_data = InstanceData('dicom', dicom_data_type, instance)

            # update meta with dicom placeholders
            self.updateMeta(dicom_data)

            # confirm 
            if os.path.isdir(dicom_data.abspath):
                dicom_data.confirm()

        # add instance to data handler
        self.config.data.instances = instances

    def scanSourceDir(self, input_dir: str) -> InputDirStructure:

        # check for only dicom files / only folders
        hasOnlyDicomFiles: bool = True
        hasOnlyFolders: bool = True

        # scan first level of input dir
        for d in os.listdir(input_dir):
            if not os.path.isfile(os.path.join(input_dir, d)) or not d.endswith(".dcm"):
                hasOnlyDicomFiles = False
            if not os.path.isdir(os.path.join(input_dir, d)):
                hasOnlyFolders = False

        # return
        if hasOnlyDicomFiles:
            return InputDirStructure.FLAT
        elif hasOnlyFolders: 
            return InputDirStructure.SERIES
        else:
            return InputDirStructure.UNKNOWN

    def importSingleInstance(self, input_dir: str, sorted_dir: str) -> None:
        
        # verbose
        self.v("> importing single instance")

        # create new instance
        #  as we just have one instance, we use the base folder
        instance = Instance(sorted_dir)
        instance.attr['sid'] = 'inst0' 

        # append instance to data handler to resolve dc chains corectly / automatically
        self.config.data.addInstance(instance)

        # create dicom data
        dicom_data_meta = self.meta.copy()
        dicom_data_type = DataType(FileType.DICOM, CT)
        dicom_data = InstanceData('dicom', dicom_data_type, instance)

        # copy the dicom data
        #  the instance root direcotry is editable and we store all generated data there.
        #  Hence, it makes sense to copy the input data to hava an transparent overview of all data relevant to an instance bundled together.
        #  However, instead of copying the data, we could also just link it with an absolute path (especially if we notice any performance issues).
        shutil.copytree(input_dir, dicom_data.abspath)

        # update meta with dicom placeholders
        self.updateMeta(dicom_data)

        # confirm data is where we expect it to be
        if os.path.isdir(dicom_data.abspath):
            dicom_data.confirm()

        # add instance to data handler
        # self.config.data.instances = [instance]

    def importMultipleInstances(self, input_dir: str, sorted_dir: str) -> None:
        
        # iterate sorted data and generate a new instance with the dicom data 
        instances_n = len(os.listdir(input_dir))
        for i, sid in enumerate(os.listdir(input_dir)):
            self.v(f"> importing instance ({i+1}/{instances_n}): ", sid)
            
            # create new instance
            instance = Instance(os.path.join(sorted_dir, sid))
            instance.attr['sid'] = sid
            
            # append instance to data handler to resolve dc chains corectly / automatically
            self.config.data.addInstance(instance)

            # create dicom data
            dicom_data_meta = self.meta.copy()
            dicom_data_type = DataType(FileType.DICOM, dicom_data_meta)
            dicom_data = InstanceData('dicom', dicom_data_type, instance)

            # copy the dicom data
            #  the instance root direcotry is editable and we store all generated data there.
            #  Hence, it makes sense to copy the input data to hava an transparent overview of all data relevant to an instance bundled together.
            #  However, instead of copying the data, we could also just link it with an absolute path (especially if we notice any performance issues).
            shutil.copytree(os.path.join(input_dir, sid), dicom_data.abspath)

            # update meta with dicom placeholders
            self.updateMeta(dicom_data)

            # confirm 
            if os.path.isdir(dicom_data.abspath):
                dicom_data.confirm()

    def task(self) -> None:

        # resolve the input directory
        source_dc = DirectoryChain(path=self.source_dir, parent=self.config.data.dc)
        import_dc = DirectoryChain(path=self.import_dir, parent=self.config.data.dc)

        self.v("> source input dir: ", self.source_dir, " --> ", source_dc.abspath)
        self.v("> import sort  dir: ", self.import_dir, " --> ", import_dc.abspath)

        # either sort data and import or only import from restricted input strucure
        if self.sort_data:

            # sort data and import
            self.sort(source_dc.abspath, import_dc.abspath, self.structure)
            self.importSorted(import_dc.abspath)

        else:
            self.v()
            self.v("> bypassing sorting process")

            # scan input structure
            source_dir_structure = self.scanSourceDir(source_dc.abspath)
            print("> source dir structure: ", source_dir_structure)

            # import data depending on input structure
            if source_dir_structure == InputDirStructure.FLAT:
                self.importSingleInstance(source_dc.abspath, import_dc.abspath) # Note: import_dc.abspath overrides instance with an abspath // self.import_dir instead?
            elif source_dir_structure == InputDirStructure.SERIES:
                self.importMultipleInstances(source_dc.abspath, import_dc.abspath)
            else:
                raise ValueError("Error: input directory structure is unknown. Cannot determine if this is a single series or multiple series.")
            