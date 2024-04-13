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
import shutil

from enum import Enum
from typing import List
from mhubio.core import Module, Instance, InstanceData, DataType, Meta, FileType, DirectoryChain, IO, SEG
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
@IO.Config('merge', bool, True, the="flag to merge related dicom data into one instance")
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
    merge: bool 
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

        # run command
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
                    meta_update[k] = "" # empty string as placeholder

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
        dicom_data_type = DataType(FileType.DICOM, dicom_data_meta)
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

    def combine(self) -> None:
        
        # get all instances
        instances = self.config.data.instances
        
        # find all related instances
        #  filter for all instances, that contain at least one file of type dicom and a modality set to segmentation
        # NOTE: should we consider removing the DICOMSEG filetype and use DICOM+SEG as the new standard or is DICOM always a folder based
        #       format and SEG/RTSTRUCT are filebased? For now, we keep it defined as the latter (which is also consistent with how we handle other file formats).
        related_instances = list(filter(lambda i: any(d.type.ftype == FileType.DICOM and (d.type.meta <= SEG or d.type.meta <= Meta(mod="RTSTRUCT")) for d in i.data), instances))
                    
        # print related instances
        self.v()
        self.v("> related instances: ", len(related_instances))
        for i in related_instances:
            self.v("> -", i.abspath)
            
        # read the dicom source image SID for each related instance
        #rinst = related_instances[0]
        for rinst in related_instances:
        
            # print rinst abspath
            self.log.debug()
            self.log.debug("> rinst abspath: ", rinst.abspath)

            # get dicom data 
            #  we expect every instance to contain exactly one file data of mhub type DICOM.
            #  we furthermore expect each file to be a dicomseg or rtstruct file and thus be exactly one file
            #  NOTE: the mhub DICOM filetype always points to a folder. We hace DICOMSEG and RTSTRUCT file types that point to the file itself.
            #        All files are imported with DICOM file type and their Modality header is by default read into the mod Meta attribute.
            #        We then later check if the modality is SEG or RTSTRUCT and change the file type accordingly.
            assert len(rinst.data) == 1
            rdicom = rinst.data.get(0)
            self.log.debug("> rdicom: ", rdicom.abspath)
            rdicom_files = os.listdir(rdicom.abspath)
            
            assert len(rdicom_files) == 1
            rdicom_file = rdicom_files[0]
            self.log.debug("> rdicom_file: ", rdicom_file)
            
            # read dicom headers
            ds = pydicom.read_file(os.path.join(rdicom.abspath, rdicom_file))
            
            # lookup source dicom sid from segmentation file dicom headers
            series_uid = None
            if rdicom.type.meta <= Meta(mod="SEG"):
                
                # (0008,1115) ReferencedSeriesSequence -> (fffe,e000) Item -> (0020,000e) SeriesInstanceUID
                ref_series = ds.ReferencedSeriesSequence[0]
                series_uid = ref_series.SeriesInstanceUID
                self.log.debug("> series_uid: ", series_uid)
            
            elif rdicom.type.meta <= Meta(mod="RTSTRUCT"):
                
                # (3006,0010) ReferencedFrameOfReferenceSequence -> (fffe,e000) Item -> (3606,0012) RTReferencedStudySequence -> (fffe,e000) Item -> (3606,0014) RTReferencedSeriesSequence -> (fffe,e000) Item -> (0020,000e) SeriesInstanceUID
                ref_series = ds.ReferencedFrameOfReferenceSequence[0].RTReferencedStudySequence[0].RTReferencedSeriesSequence[0]
                series_uid = ref_series.SeriesInstanceUID
                self.log.debug("> series_uid: ", series_uid)
            
            # stop if no series uid was found
            if series_uid is None:
                self.log.debug("> no series uid found for instance: ", rinst.abspath)
                continue
            
            # find instance with the same series UID
            parent_instances: List[Instance] = list(filter(lambda i: i.attr['sid'] == series_uid, instances))
            self.log.debug("> parent_instance: ", parent_instances)
            
            assert len(parent_instances) == 1
            parent_instance: Instance = parent_instances[0]
            self.log.debug("> parent_instance: ", parent_instance.abspath)
            
            # create a new datatype pointing to the file
            if rdicom.type.meta <= Meta(mod="SEG"):
                rinst_data = InstanceData(
                    os.path.join(rdicom.abspath, rdicom_file), 
                    DataType(FileType.DICOMSEG, rdicom.type.meta))
                
            elif rdicom.type.meta <= Meta(mod="RTSTRUCT"):
                rinst_data = InstanceData(
                    os.path.join(rdicom.abspath, rdicom_file), 
                    DataType(FileType.RTSTRUCT, rdicom.type.meta))
            
            # add data to parent instance
            parent_instance.addData(rinst_data)
            
            # confirm data
            if os.path.isfile(os.path.join(rdicom.abspath, rdicom_file)):
                rinst_data.confirm()
            
            # remove related instance
            self.config.data.instances.remove(rinst)

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
            
        # combine instances of dicomseg and dicom files if linked
        if self.merge:
            self.combine()