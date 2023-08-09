"""
-------------------------------------------------
MHub - RT-Struct Conversion Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import List
from mhubio.core import Module, Instance, InstanceData, InstanceDataCollection, DataType, IO

import SimpleITK as sitk
from segdb.classes.Segment import Segment
from rt_utils import RTStructBuilder


@IO.ConfigInput('source_segs', 'nifti|nrrd|mha:mod=seg:roi=*', the="target segmentation files to convert to dicomseg")
@IO.ConfigInput('target_dicom', 'dicom:mod=ct', the="dicom data all segmentations align to")
@IO.Config('skip_empty_slices', bool, True, the='flag to skip empty slices')
@IO.Config('converted_file_name', str, 'seg.dcm', the='name of the converted file')
@IO.Config('bundle_name', str, None, the="bundle name converted data will be added to")
@IO.Config('segment_id_meta_key', str, 'roi', the='meta key used to identify the roi in the dicomseg json config file')
@IO.Config('use_pin_hole', bool, False, the='flag for pin holes. If set to true, lines will be erased through your mask such that each separate region within your image can be encapsulated via a single contour instead of contours nested within one another. Use this if your RT Struct viewer of choice does not support nested contours / contours with holes.')
@IO.Config('approximate_contours', bool, True, the='flag defines whether or not approximations are made when extracting contours from the input mask. Setting this to false will lead to much larger contour data within your RT Struct so only use this if as much precision as possible is required.')
class RTStructConverter(Module):

    source_segs: List[DataType]
    target_dicom: DataType
    skip_empty_slices: bool
    converted_file_name: str
    bundle_name: str
    segment_id_meta_key: str
    use_pin_hole: bool
    approximate_contours: bool

    @IO.Instance()
    @IO.Inputs('source_segs', the="data to be converted")
    @IO.Input('target_dicom', the="dicom used as reference for the conversion")
    @IO.Output('out_data', path=IO.C('converted_file_name'), dtype='rtstruct:mod=seg', data='target_dicom', bundle=IO.C('bundle_name'), auto_increment=True, the="converted data")
    def task(self, instance: Instance, source_segs: InstanceDataCollection, target_dicom: InstanceData, out_data: InstanceData) -> None:
        
        # Create new RT Struct. Requires the DICOM series path for the RT Struct.
        rtstruct = RTStructBuilder.create_new(dicom_series_path=target_dicom.abspath)

        # extract and populate data 
        for source_seg in source_segs:

            # extract segments from sitk image
            mask_sitk = sitk.ReadImage(source_seg.abspath)

            # get image array 
            mask_array = sitk.GetArrayFromImage(mask_sitk)

            # check format
            #  masks can be stored either as class labels (integers) 
            #  or binary maps in a separate dimension.
            num_channels = mask_sitk.GetNumberOfComponentsPerPixel()

            # for now, we won't support binary masks in a separate dimension.
            if num_channels > 1:
                print("> Mask Shape:  ", mask_array.shape)
                raise Exception("Image data is stored as binary masks in a separate dimention. We currently do not support this format.")

            # get segment ids from meta
            segment_ids = source_seg.type.meta[self.segment_id_meta_key].split(",")

            # iterate over all segments in the image
            for label_id, segment_id in enumerate(segment_ids):
                    
                # get mask (ignore bg label_id == 0)
                if num_channels == 1:
                    mask = mask_array == (label_id + 1)
                else:
                    # NOTE: to support either format, we can select the mask from the array but need to identify the right dimension first!
                    # mask = mask_array[label_id]
                    raise Exception()

                # skip empty slices
                if self.skip_empty_slices and mask.sum() == 0:
                    print(f"Skipping empty slice {segment_id} ({label_id+1}).")
                    continue

                # get segment instance from SegDB or use fallback values
                try:
                    segment = Segment(segment_id)
                    segment_color = segment.getColor()
                    color = segment_color.getComponents() if segment_color else [0,0,0] 
                    name = segment.getName()
                except:
                    print(f"Segment {segment_id} not found in SegDB.")
                    color = None
                    name = segment_id
                
                # add segment to rtstruct
                try:
                    rtstruct.add_roi(
                        mask=mask.transpose(1, 2, 0).astype(bool), 
                        color=color, # type: ignore # FIXME: use Optionals in rtstruct.add_roi
                        name=name,
                        use_pin_hole=self.use_pin_hole,
                        approximate_contours=self.approximate_contours
                    )

                except Exception as e:
                    print(f"Error adding segment '{segment_id}' to RT Struct: {str(e)}")

        # save rt struct
        rtstruct.save(out_data.abspath)