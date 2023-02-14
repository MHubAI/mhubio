# YML DicomSeg Config (alpha)
This *package* aims to standardize the representation of segmented structures (ROI) in dicom seg.
Each ROI is assigned a unique name consisting of uppercase letters and underscores only (case in-sensitive). Spaces and other special characters aren't allowed to make the name as usable as possible.

## Database
The core is a relational database that consists of four tables for segmentations, categories, types and modifyers.

## YML Seg
The yml file has a very simple structure.
In block *dicomseg* general parameters for the [dcmqi dicom seg generator](https://qiicr.gitbook.io/dcmqi-guide/opening/cmd_tools/seg/itkimage2segimage) are defined 
In the block *segments* the available ROI are listed with their unique name as key and their file (path and) name as value.

```yml
# example seg.yml for 
dicomseg:
  BodyPartExamined: WHOLEBODY
  ClinicalTrialCoordinatingCenterName: dcmqi
  ClinicalTrialSeriesID: '0'
  ClinicalTrialTimePointID: '1'
  ContentCreatorName: IDC
  ContentDescription: Image segmentation
  ContentLabel: SEGMENTATION
  InstanceNumber: '1'
  SegmentAlgorithmName: Example
  SegmentAlgorithmType: AUTOMATIC
  SeriesDescription: Segmentation
  SeriesNumber: '42'
segments:
  ROI1: segmentation1.nii.gz
  ROI2: segmentation2.nii.gz
```

## Generate JSON config 
Methods are available to generate a [json config](http://qiicr.org/dcmqi/#/seg) for the [dcmqi dicom seg generator](https://qiicr.gitbook.io/dcmqi-guide/opening/cmd_tools/seg/itkimage2segimage).

Use the *exportJsonMeta* method to generate a config json file based on a yml segmentation file and a list of segmentation files. The output filename and path for the generated json file can be specified as the third parameter. For each segmentation file, the unique segmentation name is looked up in the yml file (assuming the file is defined there) and a json block is generated. The order of the list of input files is maintained. The function returns a 2-tupel with the filename of the generated json file and the final file list containing only the defined files.

```python
yaml_file = '/path/to/seg.yml'
file_list = [
    '/path/to/segmentation1.nii.gz',
    '/path/to/segmentation2.nii.gz',
    ...
]

tmp_json_file, file_list = exportJsonMeta(yaml_file, file_list)
```

