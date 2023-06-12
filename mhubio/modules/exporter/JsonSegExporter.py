"""
-------------------------------------------------
MHub - Export a json file that describes the
       segmentations contained in a 
       nifti / nrrd file.
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import List
from mhubio.core import Module, IO, Instance, InstanceData, InstanceDataCollection, DataType
import json, os

@IO.Config('source_segs', List[DataType], ['nifti:mod=seg:roi=*', 'nrrd:mod=seg:roi=*'], factory=IO.F.list(DataType.fromString), the='target segmentation files to convert to dicomseg')
@IO.Config('segment_id_meta_key', str, 'roi', the='meta key used to identify the roi in the dicomseg json config file')
class JsonSegExporter(Module):

    source_segs: List[DataType]
    segment_id_meta_key: str

    @IO.Instance()
    @IO.Inputs('in_datas', IO.C("source_segs"), the="data segmentation information is exported for")
    @IO.Output('out_data', path='segdef.json', dtype='json:mod=seg', the="json file containing segmentation information")
    def task(self, instance: Instance, in_datas: InstanceDataCollection, out_data: InstanceData) -> None:

        # generate json
        jseg = []

        # iterate files
        for in_data in in_datas:

            # get rois
            rois = in_data.type.meta.getValue(self.segment_id_meta_key).split(',')

            # construct json
            jseg.append({
                'file': os.path.basename(in_data.abspath),
                'labels': {(labelID+1): labelName for labelID, labelName in enumerate(rois)}
            })

        # store json
        with open(out_data.abspath, 'w') as f:
            json.dump(jseg, f, indent=4)
    