"""
-------------------------------------------------
MHub - Module to extract labels from a
       multi class segmentation file and generate
       a binary segmentation file for each
       segmentation
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

import os, uuid, json
import SimpleITK as sitk
from mhubio.core import Module, Instance, InstanceDataCollection, InstanceData, IO, DataType, FileType, Meta, InstanceDataBundle, SEG
from typing import List, Union, Tuple
from segdb.classes.Segment import Segment

def str2lst(string: Union[List[str], str]) -> list:
    if isinstance(string, str):
        return string.split(',')
    else:
        return string

@IO.ConfigInput('target_dicom', 'dicom:mod=ct|mr', the='Dicom image file.')
@IO.ConfigInput('in_datas', 'rtstruct:mod=seg', the='Dicom segmentation file.')
@IO.Config('bundle', str, 'nifti', the='Bundle name converted data will be added to')
@IO.Config('roi', list, [], factory=str2lst, the='Komma separated list of SegDB IDs in the order of the segments in the dicomseg file.')
class RTStructExtractor(Module):

    bundle: str
    roi: list
    
    @IO.Instance()
    @IO.Input("target_dicom", the="input dicom data to extract segmentationd from")
    @IO.Inputs("in_datas", the="dicomseg files related to the target dicom that will be converted into nifti files")
    @IO.Outputs("out_datas", "[basename]_[d:roi].nii.gz", "nifti:mod=seg")
    def task(self, instance: Instance, target_dicom: InstanceData, in_datas: InstanceDataCollection, out_datas: InstanceDataCollection) -> None:
        
        # create bundle for output data
        bundle = instance.getDataBundle(self.bundle)
        bundle.dc.makedirs(is_file=False)
        
        # iterate all dicomseg files 
        for in_data in in_datas:
            self.process_rtstruct(in_data, target_dicom, bundle, out_datas)
        
    def make_seg_fname(self, segment_id: int, segment_name: str) -> str:
        clean_segment_name = "".join([c for c in segment_name.lower() if c.isalnum() or c == " "]).replace(" ", "_")
        clean_segment_name = clean_segment_name[:30] # limit to 30 characters
        return f"lbl{str(segment_id).zfill(3)}-{clean_segment_name}.nii.gz"
        
    def process_rtstruct(self, in_data: InstanceData, target_dicom: InstanceData, bundle: InstanceDataBundle, out_datas: InstanceDataCollection) -> None:
        
        # create a temp folder
        temp_folder = self.config.data.requestTempDir("RTStructExtractor")
        
        # define temp output files
        ss_img_file = os.path.join(temp_folder, "ss.nii.gz")
        ss_list_file = os.path.join(temp_folder, "ss.txt")
        labelmap_file = os.path.join(temp_folder, "labelmap.nii.gz")
        
        # convert RT-Struct into nifti with plastimatch
        cmd = [
            "plastimatch",
            "convert",
            "--input", in_data.abspath,
            "--output-ss-img", ss_img_file,
            "--output-ss-list", ss_list_file,
            "--output-labelmap", labelmap_file,
            "--referenced-ct", target_dicom.abspath
        ]
        
        # run command
        self.log.debug("Running command: ", cmd)
        self.subprocess(cmd, text=True)
        
        
        # extract roi if not specified manually from the config
        if self.roi:
            
            # use the manually specified roi
            # NOTE: manual specifying ROI doesnt work if there are multiple (>1) DICOMSEG files available per instance
            self.log.debug("captured segmentation ids (manual roi) from config: ", self.roi)
            segmentation_segdb_ids = self.roi
        
        else:
          
            # iterate all segments from the ss list file
            # NOTE: the ss list file contains the segment id, rgb color (space separated) and name, separated by "|"
            #       e.g. "0|255 0 0|Segment 1". 
            # NOTE: the first segment has ID=0 (which is usually used for background but here is the first segment)
            segmentation_segdb_ids = []
            with open(ss_list_file, "r") as f:
                for line in f:
                  
                    # extract segment id and name
                    segment_id_str, segment_rgb_str, segment_name = line.strip().split("|")
                    segment_id: int = int(segment_id_str) + 1
                    segment_rgb: Tuple[int, ...] = tuple(map(int, segment_rgb_str.split(" ")))

                    # debug message
                    self.log.debug(f"segment-{segment_id}-config", {"id": segment_id, "rgb": segment_rgb, "name": segment_name})

                    # try to find a segment with the same id in the SegDB
                    # NOTE: this is a small stretch but to stay consistent with the RTStructConverter, we 
                    #       try to find a segment with the same name (and rgb color?) in the SegDB.
                    segment = Segment.findByName(segment_name)
                    
                    if segment is not None and len(segment) == 1:
                        segmentation_segdb_ids.append(segment[0].getID())
                    elif segment is not None and len(segment) > 1:
                        self.log.warning(f"Multiple segments found with the same name '{segment_name}'. SegDB matching skipped!!")
                        segmentation_segdb_ids.append(segment_name)
                    else:
                        segmentation_segdb_ids.append(segment_name)
            
            # debug log
            self.log.debug("captured segmentation ids (auto roi) from segdb meta.json config: ", segmentation_segdb_ids)
            
            
        # read labelmap file
        labelmap_itk = sitk.ReadImage(labelmap_file)
         
        # extract binary label for each segment and add to output data with simple itk
        for segment_id, segment_name in enumerate(segmentation_segdb_ids):
             
            # label id (1-indext, 0=bg)
            label_id = segment_id + 1
             
            # transfer metadata from input data
            out_data_fname = self.make_seg_fname(label_id, segment_name)
            out_data_type = DataType(FileType.NIFTI, Meta(origin="rtstruct") + in_data.type.meta + SEG)
             
            # define output file
            out_data = InstanceData(
                path=os.path.join(bundle.abspath, out_data_fname),
                type=out_data_type,
                bundle=bundle,
                auto_increment=True
            )
            
            # extend the meta data
            # NOTE: shall we use "roi" even for non-segdb ids?
            out_data.type.meta += Meta(roi=segment_name)
                
            # extract binary mask for the segment by segment_id
            mask_itk = labelmap_itk == label_id
            
            # overwrite output file with aligned image data
            sitk.WriteImage(mask_itk, out_data.abspath)
            
            # add output data file to collection
            out_datas.add(out_data)