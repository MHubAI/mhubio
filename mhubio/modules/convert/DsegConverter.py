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
import os, subprocess

from segdb.tools import DcmqiDsegConfigGenerator

@IO.ConfigInput('source_segs', 'nifti|nrrd|mha:mod=seg:roi=*', the="target segmentation files to convert to dicomseg")
@IO.ConfigInput('target_dicom', 'dicom:mod=ct', the="dicom data all segmentations align to")
#@IO.Config('source_segs', List[DataType], ['nifti:mod=seg:roi=*', 'nrrd:mod=seg:roi=*'], factory=IO.F.list(DataType.fromString), the='target segmentation files to convert to dicomseg')
#@IO.Config('target_dicom', DataType, 'dicom:mod=ct', factory=DataType.fromString, the='dicom data all segmentations align to')
@IO.Config('skip_empty_slices', bool, True, the='flag to skip empty slices')
@IO.Config('converted_file_name', str, 'seg.dcm', the='name of the converted file')
@IO.Config('bundle_name', str, None, the="bundle name converted data will be added to")
@IO.Config('model_name', str, 'MHub-Model', the="model name populated in the dicom seg SeriesDescription attribute")
@IO.Config('json_config_path', str, None, the='path to the dicomseg json config file')    
@IO.Config('segment_id_meta_key', str, 'roi', the='meta key used to identify the roi in the dicomseg json config file')
@IO.Config('body_part_examined', str, 'WHOLEBODY', the='body part examined by the model (available values: https://dicom.nema.org/medical/dicom/current/output/chtml/part16/chapter_L.html)')
class DsegConverter(Module):

    source_segs: List[DataType]
    target_dicom: DataType
    skip_empty_slices: bool
    converted_file_name: str
    bundle_name: str
    model_name: str
    json_config_path: str
    segment_id_meta_key: str
    body_part_examined: str

    @IO.Instance()
    @IO.Inputs('source_segs', the="data to be converted")
    @IO.Input('target_dicom', the="dicom used as reference for the conversion")
    #@IO.Inputs("in_segs", IO.C("source_segs"), the="input data to convert to dicomseg")
    #@IO.Input("in_dicom", IO.C("target_dicom"), the="input dicom data to convert to dicomseg")
    @IO.Output('out_data', path=IO.C('converted_file_name'), dtype='dicomseg:mod=seg', data='target_dicom', bundle=IO.C('bundle_name'), auto_increment=True, the="converted data")
    def task(self, instance: Instance, source_segs: InstanceDataCollection, target_dicom: InstanceData, out_data: InstanceData) -> None:
        
        # either use a custom json config or generate based on meta label (default key: roi)
        if self.json_config_path is not None:

            # sort files alphabetically
            file_list = sorted([source_seg.abspath for source_seg in source_segs])   
            json_config_path = self.json_config_path

        else:

            # generate json meta generator instance
            generator = DcmqiDsegConfigGenerator(
                model_name = self.model_name,
                body_part_examined = self.body_part_examined,
            )

            # sort DTQ filter results by path name alphabetically
            source_segs.sort()

            # extract and populate data 
            for source_seg in source_segs:
                generator.addItem(
                    file = source_seg.abspath, 
                    segment_ids = source_seg.type.meta[self.segment_id_meta_key].split(","),
                    model_name = source_seg.type.meta.getValue('model'),
                )

            # store json in temp dir
            tmp_dir = self.config.data.requestTempDir('dseg_converter')
            json_config_path = os.path.join(tmp_dir, "temp-meta.json")
            generator.save(config_file=json_config_path, overwrite=True)

            # get file list (comma separated string)
            file_list = generator.getFileList()

            # create outdir if required
            # TODO: can we handle this during bundle creation or in IO decorator?
            if not os.path.isdir(os.path.dirname(out_data.abspath)):
                os.makedirs(os.path.dirname(out_data.abspath))

        # build command
        bash_command  = ["itkimage2segimage"]
        bash_command += ["--inputImageList", ",".join(file_list)]
        bash_command += ["--inputDICOMDirectory", target_dicom.abspath]
        bash_command += ["--outputDICOM", out_data.abspath]
        bash_command += ["--inputMetadata", json_config_path]

        # add skip empty slices flag
        if self.skip_empty_slices == True:
            bash_command += ["--skip"]

        # run command
        self.v(">> run: ", " ".join(bash_command))
        self.subprocess(bash_command, text=True)