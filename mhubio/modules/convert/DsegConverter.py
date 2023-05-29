"""
-------------------------------------------------
MHub - DicomSeg Conversion Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import List
from mhubio.core import Module, Instance, InstanceData, InstanceDataCollection, DataType, IO
from mhubio.utils.ymldicomseg import buildSegmentJsonBySegId
import os, subprocess, json

@IO.Config('source_segs', List[DataType], ['nifti:mod=seg:roi=*', 'nrrd:mod=seg:roi=*'], factory=IO.F.list(DataType.fromString), the='target segmentation files to convert to dicomseg')
@IO.Config('target_dicom', DataType, 'dicom:mod=ct', factory=DataType.fromString, the='dicom data all segmentations align to')
@IO.Config('skip_empty_slices', bool, True, the='flag to skip empty slices')
@IO.Config('converted_file_name', str, 'seg.dcm', the='name of the converted file')
@IO.Config('bundle_name', str, None, the="bundle name converted data will be added to")
@IO.Config('model_name', str, 'MHub-Model', the="model name populated in the dicom seg SeriesDescription attribute")
@IO.Config('json_config_path', str, None, the='path to the dicomseg json config file')    
@IO.Config('segment_id_meta_key', str, 'roi', the='meta key used to identify the roi in the dicomseg json config file')
class DsegConverter(Module):

    source_segs: List[DataType]
    target_dicom: DataType
    skip_empty_slices: bool
    converted_file_name: str
    bundle_name: str
    model_name: str
    json_config_path: str
    segment_id_meta_key: str

    def generateJsonMeta(self, definition):

        # json meta
        json_meta = {
            'BodyPartExamined': 'WHOLEBODY',
            'ClinicalTrialCoordinatingCenterName': 'dcmqi',
            'ClinicalTrialSeriesID': '0',
            'ClinicalTrialTimePointID': '1',
            'ContentCreatorName': 'MHub',
            'ContentDescription': 'Image segmentation',
            'ContentLabel': 'SEGMENTATION',
            'InstanceNumber': '1',
            'SeriesDescription': self.model_name,
            'SeriesNumber': '42',
            'segmentAttributes': []
        }

        # json meta present for each roi
        segment_base_attributes = {
            'SegmentAlgorithmType': 'AUTOMATIC',
            'SegmentAlgorithmName': 'Platipy',
        }

        # generate json meta per file and segments
        json_meta['segmentAttributes'] = [[{**buildSegmentJsonBySegId(roi, labelID + 1), **segment_base_attributes} for labelID, roi in enumerate(rois)] for rois in definition.values()]
        file_list = list(definition.keys())

        return json_meta, file_list

    @IO.Instance()
    @IO.Inputs("in_segs", IO.C("source_segs"), the="input data to convert to dicomseg")
    @IO.Input("in_dicom", IO.C("target_dicom"), the="input dicom data to convert to dicomseg")
    @IO.Output('out_data', path=IO.C('converted_file_name'), dtype='dicomseg:mod=seg', data='in_dicom', bundle=IO.C('bundle_name'), auto_increment=True, the="converted data")
    def task(self, instance: Instance, in_segs: InstanceDataCollection, in_dicom: InstanceData, out_data: InstanceData) -> None:
        
        # either use a custom json config or generate based on meta label (default key: roi)
        if self.json_config_path is not None:

            # sort files alphabetically
            file_list = sorted([in_seg.abspath for in_seg in in_segs])   
            json_config_path = self.json_config_path

        else:

            # get ROI - file construct
            roi_def = {in_seg.abspath: in_seg.type.meta[self.segment_id_meta_key].split(",") for in_seg in in_segs}

            # generate the json meta in a temp directory 
            json_meta, file_list = self.generateJsonMeta(roi_def)
            tmp_dir = self.config.data.requestTempDir('dseg_converter')
            json_config_path = os.path.join(tmp_dir, "temp-meta.json")

            # temporarily store json
            with open(json_config_path, 'w') as f:
                json.dump(json_meta, f)

            # create outdir if required
            # TODO: can we handle this during bundle creation or in IO decorator?
            if not os.path.isdir(os.path.dirname(out_data.abspath)):
                os.makedirs(os.path.dirname(out_data.abspath))

        # build command
        bash_command  = ["itkimage2segimage"]
        bash_command += ["--inputImageList", ','.join(file_list)]
        bash_command += ["--inputDICOMDirectory", in_dicom.abspath]
        bash_command += ["--outputDICOM", out_data.abspath]
        bash_command += ["--inputMetadata", json_config_path]

        # add skip empty slices flag
        if self.c["skip_empty_slices"] == True:
            bash_command += ["--skip"]

        # run command
        try: 
            self.v(">> run: ", " ".join(bash_command))
            _ = subprocess.run(bash_command, check = True, text = True)
        except Exception as e:
            self.v("Error while running dicomseg-conversion for instance " + str(instance) + ": " + str(e))

        # check if output file was created
        #if os.path.isfile(out_data.abspath):
        #    out_data.confirm()