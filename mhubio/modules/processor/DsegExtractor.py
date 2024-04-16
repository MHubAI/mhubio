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
from typing import List, Union
from segdb.classes.Segment import Segment

def str2lst(string: Union[List[str], str]) -> list:
    if isinstance(string, str):
        return string.split(',')
    else:
        return string

@IO.ConfigInput('target_dicom', 'dicom:mod=ct|mr', the='Dicom image file.')
@IO.ConfigInput('in_datas', 'dicomseg:mod=seg', the='Dicom segmentation file.')
@IO.Config('bundle', str, 'nifti', the='Bundle name converted data will be added to')
@IO.Config('roi', list, [], factory=str2lst, the='Komma separated list of SegDB IDs in the order of the segments in the dicomseg file.')
class DsegExtractor(Module):

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
        
        # read in the target dicom to then later align all the segmentations to the target z height
        sitk_dcm_reader = sitk.ImageSeriesReader()
        img_dcm_files = sitk_dcm_reader.GetGDCMSeriesFileNames(target_dicom.abspath)
        sitk_dcm_reader.SetFileNames(img_dcm_files)
        img_itk = sitk_dcm_reader.Execute()
        
        # warning if roi is specified and multiple dicomseg files are available
        if self.roi and len(in_datas) > 1:
            self.log.warning("Multiple dicomseg files available but only one roi specified. The roi will be used for all files.")
        
        # iterate all dicomseg files 
        for in_data in in_datas:
            self.process_dicomseg(in_data, img_itk, bundle, out_datas)
            
    def process_dicomseg(self, in_data: InstanceData, target_dicom_img_itk: sitk.Image, bundle: InstanceDataBundle, out_datas: InstanceDataCollection) -> None:
            
        # log
        self.log("in_data", in_data)
        self.log("bundle", bundle)
        self.log("bundle path: ", bundle.abspath, os.path.exists(bundle.abspath))
        
        # random 10 digit run id
        run_id = uuid.uuid4().hex[:10]
        
        # gebnerate command
        bash_command = [
            "segimage2itkimage",
            "--outputType", "nifti",
            "--outputDirectory", bundle.abspath,
            "--inputDICOM", in_data.abspath,
            "--prefix", run_id
        ]
        
        # run command
        self.subprocess(bash_command, text=True)
        
        # extract roi if not specified manually from the config
        if self.roi:
            
            # use the manually specified roi
            # NOTE: manual specifying ROI doesnt work if there are multiple (>1) DICOMSEG files available per instance
            segmentation_segdb_ids = self.roi
        
        else:
            
            # path to the dicomseg config file (meta.json) generated in the output folder
            config_file = os.path.join(bundle.abspath, f"{run_id}-meta.json")
        
            # read the meta.json config file
            with open(config_file, "r") as f:
                dseg_config = json.load(f)
            
            # iterate all segments in the meta.json config file and extract the roi from the SegDB segment 
            # NOTE: for old/outdated or non MHub conforming dicomseg files 
            #       you might need to manually specify the roi in the config instead
            segmentation_segdb_ids = []
            for segment_idx, segment_config in enumerate(dseg_config["segmentAttributes"]):
                
                # NOTE: we expect each segment to contain exactly one structure and therefore each 
                #       generated nifti file to be a binary mask
                assert len(segment_config) == 1
                segment_config = segment_config[0]
                
                # print segment config
                self.log.debug(f"segment-{segment_idx+1}-config", segment_config)
                
                # try to generate a SegDB segment from the json
                try:
                    segment = Segment.fromJSON(segment_config)
                    segmentation_segdb_ids.append(segment.getID())
                except:
                    segmentation_segdb_ids.append(None)

            # debug log
            self.log.debug("captured segmentation ids (auto roi) from segdb meta.json config: ", segmentation_segdb_ids)
        
        # define a sitk identity transform
        identity_tfx = sitk.Transform(3, sitk.sitkIdentity)
        
        # iterate bundle and add output data
        for file in os.listdir(str(bundle.abspath)):
            
            # ignore non nifti files
            if not (file.endswith(".nii.gz") and file.startswith(run_id)):
                continue
            
            # transfer metadata from input data
            out_data_type = DataType(FileType.NIFTI, Meta(origin="dicomseg") + in_data.type.meta + SEG)

            # specify the output data file
            out_data = InstanceData(
                path=os.path.join(bundle.abspath, file),
                type=out_data_type,
                bundle=bundle
            )
            
            # if rois is set
            if segmentation_segdb_ids:
                
                # get index from file name (<runid>-<index>.nii.gz)
                index = int(file.split("-")[-1].split(".")[0]) - 1
            
                # extend the meta data
                out_data.type.meta += Meta(roi=segmentation_segdb_ids[index])
                
            # correct the size of the segmentation masks by applying a 
            #  id transform with simple itk
            seg_itk = sitk.ReadImage(out_data.abspath)
            
            # debug 
            self.log.debug(f"Resampling itk image {out_data.abspath}:  [{seg_itk.GetSize()} -> {target_dicom_img_itk.GetSize()}]")
            
            # ensure all masks are binary (0 = background, 1 = foreground label)
            # NOTE: nifti files generated by segimage2itkimage although binary will not contain 0 and 1 but 0 and label-id values.
            # seg_itk = sitk.Clamp(seg_itk, upperBound=1) <-- this works, but doesn't change the file type to uint8 (below is consistent with RTStructExtractor)
            seg_itk = seg_itk > 0
            
            # align the segmentation mask to the target dicom image (to get a uniform z height as per the target dicom image)
            seg_aligned_itk = sitk.Resample(seg_itk, target_dicom_img_itk, identity_tfx, sitk.sitkNearestNeighbor, 0)

            # overwrite output file with aligned image data
            sitk.WriteImage(seg_aligned_itk, out_data.abspath)
            
            # add output data file to collection
            out_datas.add(out_data)