"""
-------------------------------------------------
MHub - PNG Conversion Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
Date:   04.03.20224
-------------------------------------------------
"""

from mhubio.core import Module, Instance, InstanceDataCollection, FileType, IO
from typing import Optional
from enum import Enum
import SimpleITK as sitk
import os

class PngConverterEngine(Enum):
    ITK = 'itk'

@IO.ConfigInput('in_datas', 'dicom:mod=cr|dx', the="target data that will be converted into a png")
@IO.Config('engine', PngConverterEngine, 'itk', factory=PngConverterEngine, the='engine to use for conversion')
@IO.Config('allow_multi_input', bool, False, the='allow multiple input files')
@IO.Config('bundle_name', str, 'png', the="bundle name converted data will be added to")
@IO.Config('converted_file_name', str, '[filename].png', the='name of the converted file')
@IO.Config('overwrite_existing_file', bool, False, the='overwrite existing file if it exists')
@IO.Config('new_width', int, None, the='width of the output image (will be rescaled if set)')
class PngConverter(Module):
    """
    Conversion module that converts DICOM data into PNG.
    """

    engine: PngConverterEngine
    allow_multi_input: bool
    bundle_name: str                # TODO: make Optional[str] here and in decorator once supported
    converted_file_name: str
    overwrite_existing_file: bool
    new_width: int                  # TODO: make Optional[int] here and in decorator once supported

    @IO.Instance()
    @IO.Inputs('in_datas', the="data to be converted")
    @IO.Outputs('out_datas', path=IO.C('converted_file_name', str), dtype='png', data='in_datas', bundle=IO.C('bundle_name', str), auto_increment=True, the="converted data")
    def task(self, instance: Instance, in_datas: InstanceDataCollection, out_datas: InstanceDataCollection, **kwargs) -> None:

        # some sanity checks
        assert isinstance(in_datas, InstanceDataCollection)
        assert isinstance(out_datas, InstanceDataCollection)
        assert len(in_datas) == len(out_datas)

        # filtered collection must not be empty
        if len(in_datas) == 0:
            #self.log(f"CONVERT ERROR: no data found in instance {str(instance)}.", level="error")
            self.log.error(f"No data found in instance {str(instance)}.")
            return None

        # check if multi file conversion is enables
        if not self.allow_multi_input and len(in_datas) > 1:
            self.log.warning("Found more than one matching file but multi file conversion is disabled. Only the first file will be converted.")
            in_datas = InstanceDataCollection([in_datas.first()])

        # conversion step
        for i, in_data in enumerate(in_datas):
            out_data = out_datas.get(i)

            # check if output data already exists
            if os.path.isfile(out_data.abspath) and not self.overwrite_existing_file:
                #print("CONVERT ERROR: File already exists: ", out_data.abspath)
                self.log.error(f"File already exists: {out_data.abspath}")
                continue

            # check datatype 
            if in_data.type.ftype == FileType.DICOM:

                # extract dicom files
                dcm_files_abspaths = [os.path.join(in_data.abspath, f) for f in os.listdir(in_data.abspath) if f.endswith(".dcm")]

                # check if we have a single or multiple dicom files (2D or 3D image)
                if len(dcm_files_abspaths) > 1:
                    self.log.error("Multiple dicom files found. Only single dicom files are supported for now.")
                    
                # print overview of detected files
                self.log(f"Found {len(dcm_files_abspaths)} dicom files in {in_data.abspath}.")
                    
                # convert image with itk
                if self.engine == PngConverterEngine.ITK:
                    self.storeDicomSliceAsPng(dcm_files_abspaths[0], out_data.abspath, new_width=self.new_width)
                else:
                    self.log.error(f"Unsupported engine {self.engine}.")
                
            else:
                #print("CONVERT ERROR: unsupported file type: ", in_data.type.ftype)
                self.log.error(f"Unsupported file type: {in_data.type.ftype}.")
                continue

    @staticmethod
    def storeDicomSliceAsPng(input_file_name: str, output_file_name: str, new_width: Optional[int] = None) -> None:
        """
        Convert a single dicom slice into a png file using SimpleITK.
        """
        # read more: https://simpleitk.readthedocs.io/en/master/link_DicomConvert_docs.html
    
        image_file_reader = sitk.ImageFileReader()
        
        # only read DICOM images
        image_file_reader.SetImageIO("GDCMImageIO")
        image_file_reader.SetFileName(input_file_name)
        image_file_reader.ReadImageInformation()
        image_size = list(image_file_reader.GetSize())
    
        if len(image_size) == 3 and image_size[2] == 1:
            image_size[2] = 0
    
        image_file_reader.SetExtractSize(image_size)
        image = image_file_reader.Execute()
    
        if new_width:
            original_size = image.GetSize()
            original_spacing = image.GetSpacing()
            
            new_spacing = [
                (original_size[0] - 1) * original_spacing[0] / (new_width - 1)
            ] * 2
        
            new_height = int((original_size[1] - 1) * original_spacing[1] / new_spacing[1])
            new_size = [new_width, new_height]
                
            image = sitk.Resample(
                image1=image,
                size=new_size, # type: ignore
                transform=sitk.Transform(),
                interpolator=sitk.sitkLinear,
                outputOrigin=image.GetOrigin(),
                outputSpacing=new_spacing,
                outputDirection=image.GetDirection(),
                defaultPixelValue=0,
                outputPixelType=image.GetPixelID(),
            )
            
        # If a single channel image, rescale to [0,255]. Also modify the
        # intensity values based on the photometric interpretation. If
        # MONOCHROME2 (minimum should be displayed as black) we don't need to
        # do anything, if image has MONOCRHOME1 (minimum should be displayed as
        # white) we flip # the intensities. This is a constraint imposed by ITK
        # which always assumes MONOCHROME2.
        if image.GetNumberOfComponentsPerPixel() == 1:
            image = sitk.RescaleIntensity(image, 0, 255)
            if (image_file_reader.GetMetaData("0028|0004").strip() == "MONOCHROME1"):
                image = sitk.InvertIntensity(image, maximum=255)
            image = sitk.Cast(image, sitk.sitkUInt8)
            
        # write image
        sitk.WriteImage(image, output_file_name)
            