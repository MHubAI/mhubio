"""
-------------------------------------------------
MHub - MHA Conversion Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import  Dict, Any

from mhubio.core import Module, Instance, InstanceDataCollection, InstanceData, FileType
from mhubio.core.IO import IO

import os
import pyplastimatch as pypla # type: ignore


#@IO.Config('engine', NiftiConverterEngine, 'plastimatch', factory=NiftiConverterEngine, the='engine to use for conversion')
@IO.ConfigInput('in_datas', 'dicom|nrrd|nifti', the="target data that will be converted to mha")
@IO.Config('allow_multi_input', bool, False, the='allow multiple input files')
@IO.Config('bundle_name', str, 'mha', the="bundle name converted data will be added to")
@IO.Config('converted_file_name', str, '[filename].mha', the='name of the converted file')
@IO.Config('overwrite_existing_file', bool, False, the='overwrite existing file if it exists')
class MhaConverter(Module):
    """
    Conversion module that converts DICOM, NRRD and NIFTI data into MHA (using plastimatch).
    """

    allow_multi_input: bool
    bundle_name: str                    # TODO optional type declaration
    converted_file_name: str
    overwrite_existing_file: bool

    def plastimatch(self, instance: Instance, in_data: InstanceData, out_data: InstanceData, log_data: InstanceData) -> None:

        #print("[DRY RUN] plastimatch")
        #print("[DRY RUN] in:  ", in_data.abspath)
        #print("[DRY RUN] out: ", out_data.abspath)
        #print("[DRY RUN] log: ", log_data.abspath)
        #return

        # set input and output paths later passed to plastimatch
        convert_args_ct: Dict[str, Any] = {
            "input" : in_data.abspath,
            "output-img" : out_data.abspath
        }

        # remove old log file if it exist
        if os.path.isfile(log_data.abspath): 
            os.remove(log_data.abspath)
        
        # run conversion using plastimatch
        pypla.convert(
            verbose=self.verbose,
            path_to_log_file=log_data.abspath,
            **convert_args_ct
        )

        if os.path.isfile(log_data.abspath):
            log_data.confirm()

    @IO.Instance()
    @IO.Inputs('in_datas', the="data to be converted")
    @IO.Outputs('out_datas', path=IO.C('converted_file_name'), dtype='mha', data='in_datas', bundle=IO.C('bundle_name'), auto_increment=True, the="converted data")
    @IO.Outputs('log_datas', path='[basename].pmconv.log', dtype='log:log-task=conversion', data='in_datas', bundle=IO.C('bundle_name'), auto_increment=True, the="log generated by conversion engine")
    def task(self, instance: Instance, in_datas: InstanceDataCollection, out_datas: InstanceDataCollection, log_datas: InstanceDataCollection, **kwargs) -> None:

        # some sanity checks
        assert isinstance(in_datas, InstanceDataCollection)
        assert isinstance(out_datas, InstanceDataCollection)
        assert len(in_datas) == len(out_datas)
        assert len(in_datas) == len(log_datas)

        # filtered collection must not be empty
        if len(in_datas) == 0:
            print(f"CONVERT ERROR: no data found in instance {str(instance)}.")
            return None

        # check if multi file conversion is enables
        if not self.allow_multi_input and len(in_datas) > 1:
            print("WARNING: found more than one matching file but multi file conversion is disabled. Only the first file will be converted.")
            in_datas = InstanceDataCollection([in_datas.first()])

        # conversion step
        for i, in_data in enumerate(in_datas):
            out_data = out_datas.get(i)
            log_data = log_datas.get(i)

            # check if output data already exists
            if os.path.isfile(out_data.abspath) and not self.overwrite_existing_file:
                print("CONVERT ERROR: File already exists: ", out_data.abspath)
                continue

            # check datatype 
            if in_data.type.ftype in [FileType.DICOM, FileType.NRRD, FileType.NIFTI]:
                                
                # for nrrd files use plastimatch
                self.plastimatch(instance, in_data, out_data, log_data)

            else:
                raise ValueError(f"CONVERT ERROR: unsupported file type {in_data.type.ftype}.")