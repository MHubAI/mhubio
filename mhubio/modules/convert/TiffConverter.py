"""
-------------------------------------------------
MHub - Tiff Conversion Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from mhubio.core import Module, Instance, InstanceDataCollection, FileType, IO
import os, shutil
from pathlib import Path

# conversion dependencies
from panimg.image_builders.tiff import image_builder_tiff # type: ignore

@IO.ConfigInput('in_datas', 'dicom:mod=sm', the="target data that will be converted to mha")
@IO.Config('allow_multi_input', bool, False, the='allow multiple input files')
@IO.Config('bundle_name', str, 'tiff', the="bundle name converted data will be added to")
@IO.Config('converted_file_name', str, '[filename].tiff', the='name of the converted file')
@IO.Config('overwrite_existing_file', bool, False, the='overwrite existing file if it exists')
class TiffConverter(Module):
    """
    Conversion module that converts DICOM, NRRD and NIFTI data into MHA.
    """

    allow_multi_input: bool
    bundle_name: str                # TODO. make Optional[str] here and in decorator once supported
    converted_file_name: str
    overwrite_existing_file: bool

    @IO.Instance()
    @IO.Inputs('in_datas', the="data to be converted")
    @IO.Outputs('out_datas', path=IO.C('converted_file_name'), dtype='tiff', data='in_datas', bundle=IO.C('bundle_name'), auto_increment=True, the="converted data")
    def task(self, instance: Instance, in_datas: InstanceDataCollection, out_datas: InstanceDataCollection, **kwargs) -> None:

        # some sanity checks
        assert isinstance(in_datas, InstanceDataCollection)
        assert isinstance(out_datas, InstanceDataCollection)
        assert len(in_datas) == len(out_datas)

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

            # check if output data already exists
            if os.path.isfile(out_data.abspath) and not self.overwrite_existing_file:
                print("CONVERT ERROR: File already exists: ", out_data.abspath)
                continue

            # check datatype 
            if in_data.type.ftype == FileType.DICOM:

                # extract dicom files
                dcm_files_abspaths = [Path(os.path.join(in_data.abspath, f)) for f in os.listdir(in_data.abspath) if f.endswith(".dcm")]

                # for dicom data use a dicom image builder
                #  as we control the input (one dicom instance) we expect exactly one output. 
                #  We set None as default to avoid StopIteration exceptions in caseof an empty iterator.

                # NOTE: image_builder_tiff falls out of the naming convention, takes dicom data as input and returns an object where the path to the temporarily created tiff file is available in the file attribute.

                # NOTE: inside image_builder_tiff, the file is created as a temporary file in a tempfile.TemporaryDirectory context that closes at the end of the loop-body. Hence, we can only access the temporary file at result.file inside an actual loop. If we'd use next() like result = next(image_builder_tiff(files=dcm_files_abspaths), None), the file would be removed immediately.

                # iterate only for the first result
                for result in image_builder_tiff(files=dcm_files_abspaths):

                    # copy the tmp file if found or report an error
                    if result is not None and os.path.isfile(result.file):
                        shutil.copyfile(result.file, out_data.abspath)            
                    else: 
                        print("CONVERT ERROR: image builder returned no images.")

                    # we expect exactly 1 result, so leaving the loop here.
                    break
                
            else:
                print("CONVERT ERROR: unsupported file type: ", in_data.type.ftype)
                continue

