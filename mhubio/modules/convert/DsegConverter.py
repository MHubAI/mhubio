"""
-------------------------------------------------
MHub - DicomSeg Conversion Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import Optional

from mhubio.core import Instance, InstanceData, DataType, FileType, Meta, SEG
from .DataConverter import DataConverter
from mhubio.utils.ymldicomseg import exportJsonMeta, removeTempfile

import os, subprocess

# TODO: we should have a generator for instance data (e.g., on the Instance class)

# TODO: Dicomseg generation so far epends on the model. This should, however, be more independend. Ideally, a segmentation carries information about it's ROI in the DataType metatada (will be targeted in the upcoming DataType revision). This can be used to the generate the conversion file dynamicaly and model independend (of course each model has to populate a maping of it's segmentations but that's A simpler, B functional for other use cases too)

class DsegConverter(DataConverter):
    def convert(self, instance: Instance) -> Optional[InstanceData]:
        
        # get input data (segmentation files)
        fdata = instance.filterData(DataType(FileType.NIFTI, SEG)) #  TODO: fetach all models? standardized meta data fields required.

        # get dicom data
        dicom_data = instance.getData(DataType(FileType.DICOM))

        # output data
        out_data = InstanceData("seg.dcm", DataType(FileType.DICOMSEG, SEG)) # TODO: pass model
        out_data.instance = instance

        # get config json & input files
        if 'dicomseg_json_path' in self.c:
            # get segmentation paths list
            pred_segmasks_nifti_list = [d.abspath for d in fdata]
            
            # TODO: old approach, only valid as long all segmentations are in the same folder.
            #       we could encode the standardized segmentation names in the meta data, e.g. by utilizing the dicomseg.yml config in the ModelRunner. To discuss wheather we loop over whats available (filesystem / data filter) or whats defined (config) or use the union and report missing values.
            pred_segmasks_nifti_list = ",".join(sorted(pred_segmasks_nifti_list))

            # config (json)
            dicomseg_json_path = self.c['dicomseg_json_path']
            remove_json_config_file = False

        elif 'dicomseg_yml_path' in self.c:

            # get abs paths and a list of all filenames 
            # -> json will be generated following the fil_list order.
            # NOTE: relies on the (uninvorced) convention, that InstanceData.data is the basename 
            #       (e.g. the file name) rather than a folder structure of any depth.
            # file_list = [d.path for d in fdata]
            # NOTE: ... which is not the case for data hosted outside (here path is the abspath and base is empty). Revision or detailed documentation needed!

            file_list = [os.path.basename(d.abspath) for d in fdata]

            # config (yml->json)
            dicomseg_json_path, file_list = exportJsonMeta(self.c['dicomseg_yml_path'], file_list)
            remove_json_config_file = True

            #
            pred_segmasks_nifti_list = ",".join([d.abspath for d in fdata if os.path.basename(d.abspath) in file_list])

        else:
            raise ValueError("Configuration missing, either json or yml config is required to generate dicomseg.")

        # build command
        bash_command  = ["itkimage2segimage"]
        bash_command += ["--inputImageList", pred_segmasks_nifti_list]
        bash_command += ["--inputDICOMDirectory", dicom_data.abspath]
        bash_command += ["--outputDICOM", out_data.abspath]
        bash_command += ["--inputMetadata", dicomseg_json_path]

        if self.c["skip_empty_slices"] == True:
            bash_command += ["--skip"]

        self.v(">> run: ", " ".join(bash_command))

        # execute command
        bash_return = subprocess.run(bash_command, check = True, text = True)

        if remove_json_config_file:
            removeTempfile()

        #TODO: check success, return either None or InstanceData
        return out_data