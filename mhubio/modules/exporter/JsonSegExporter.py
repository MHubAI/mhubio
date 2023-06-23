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

from mhubio.core import Module, IO, Instance, InstanceData
from mhubio.modules.organizer.DataOrganizer import DataOrganizer
import json, os

@IO.Config('target_dir', str, '', the="path prefix.")
@IO.Config('targets', list, [], the="list of targets to organize the data into")
@IO.Config('require_data_confirmation', bool, True, the="flag if set, only confirmed files will be exported by the organizer.")
@IO.Config('segment_id_meta_key', str, 'roi', the='meta key used to identify the roi in the dicomseg json config file')

class JsonSegExporter(Module):

    target_dir: str
    targets: list
    require_data_confirmation: bool
    segment_id_meta_key: str

    @IO.Instance()
    @IO.Output('out_data', path='segdef.json', dtype='json:mod=seg', the="json file containing segmentation information")
    def task(self, instance: Instance, out_data: InstanceData) -> None:

        # generate json
        jseg = []

        # iterate target definitions
        for target_definition in self.targets:

            # extract source and target
            src_def, tar_def = target_definition.split("-->")

            # filter for data type
            in_datas = instance.data.filter(src_def, confirmed_only=self.require_data_confirmation)

            # iterate data
            for in_data in in_datas:

                try: 

                    # get segment_id_keys
                    rois_def = in_data.type.meta.getValue(self.segment_id_meta_key)

                    if not rois_def:
                        raise Exception(f"Meta key {self.segment_id_meta_key} not provided / set.")

                    # get rois
                    rois = rois_def.split(',')

                    # resolve target
                    tar_res = DataOrganizer.resolveTarget(tar_def, in_data)

                    if tar_res is None:
                        raise Exception(f"Failed to resolve target {tar_def} for {str(in_data)} {in_data.abspath}")

                    # construct path
                    in_data_path = os.path.join(self.target_dir, tar_res)

                    # construct json
                    jseg.append({
                        'file': in_data_path,
                        'labels': {(labelID+1): labelName for labelID, labelName in enumerate(rois)}
                    })

                except Exception as e:
                    self.v(f"Failed to export segmentation information for {str(in_data)} {in_data.abspath}: {e}")

        # store json
        with open(out_data.abspath, 'w') as f:
            json.dump(jseg, f, indent=4)
    