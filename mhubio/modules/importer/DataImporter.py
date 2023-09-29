"""
-------------------------------------------------
DEPRECATED MODULE - DO NOT USE
MHub - Data Importer Base Module.
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import List, Dict, Optional, Tuple
from mhubio.core import Config, Module, Instance, InstanceData, DataType, FileType, Meta, CT
import os

class IDEF:
    """ Instance definition.
        All data with the same reference (ref) will be grouped into a single instance.
        As no file operations are performed in the DataImporter base class, "ref" must also be the
        instance's folder and the last folder in the path chain of each file added under that ref.
        Note, that no ref (None) is a valid value and can be used if only a single instance is to be 
        created and all data is located in the input folder (which should then be set as the data importer's basePath).
    """
    def __init__(self, ref: Optional[str], path: str, ftype: FileType, meta: Meta) -> None:
        self.ref = ref if ref is not None else "" #if ref and type(ref) == str else str(uuid.uuid4())
        self.path = path
        self.ftype = ftype
        self.meta = meta

class DataImporter(Module):
    """
    Importer base moule and Instance generator class.
    An importer must always be the first module of any module chain.
    """

    def __init__(self, config: Config, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self.basePath: Optional[str] = None
        self._import_paths: List[IDEF] = []
        self._import_attrs: List[Tuple[str, str, str]] = []

    def setBasePath(self, path: str):
        self.basePath = path

    def _resolvePath(self, path, ref: Optional[str] = None):
        plst = [self.config.data.abspath]
        if self.basePath: plst.append(self.basePath)
        if ref: plst.append(ref)
        plst.append(path)
        return os.path.join(*plst)

    # --- Helper hethods for adding data ----
    #def addInstanceBasePath(self, base_path = str):
    #    self._import_bases.append(base_path)

    def addDicomCT(self, path: str, ref: Optional[str] = None) -> None:
        _path = self._resolvePath(path, ref)
        self.v("adding ct in dicom format with resolved path: ", _path)
        assert os.path.isdir(_path), f"Expect existing dicom directory, '{_path}' was given instead."
        assert [f for f in os.listdir(_path) if f[-4:] == '.dcm'], f"Expect at least one file ending with .dcm in {_path}."
        self._import_paths.append(IDEF(
            ref = ref,
            path = path, 
            ftype = FileType.DICOM,
            meta = CT
        ))

    def addNiftiCT(self, path: str, ref: Optional[str] = None) -> None:
        _path  = self._resolvePath(path, ref)
        self.v("adding ct in nifti format with resolved path: ", _path)
        assert os.path.isfile(_path) and (_path[-4:] == '.nii' or _path[-7:] == '.nii.gz'), f"Expect existing nifti file, '{_path}' was given instead."
        self._import_paths.append(IDEF(
            ref = ref,
            path = path, 
            ftype = FileType.NIFTI,
            meta = CT
        ))

    def addNrrdCT(self, path: str, ref: Optional[str] = None) -> None:
        _path  = self._resolvePath(path, ref)
        self.v("adding ct in nrrd format with resolved path: ", _path)
        assert os.path.isfile(_path) and (_path[-5:] == '.nrrd'), f"Expect existing nrrd file, '{_path}' was given instead."
        self._import_paths.append(IDEF(
            ref = ref,
            path = path, 
            ftype = FileType.NRRD,
            meta = CT
        ))

    # --- Other helper methods ---
    def setAttribute(self, key: str, value: str, ref: str) -> None:
        """
        Sets an attribute (key-value pair) for any instance referenced by its unique reference (ref) string. 
        Note that you can set attributes in advance, before adding data. However, instances are created only if at least one data item is associated. So if you set only one attribute, no instances will be created.
        """
        self._import_attrs.append((key, value, ref))

    def getReferenceList(self) -> List[str]:
        """
        Returns a list of all used references.
        """
        return [idef.ref for idef in self._import_paths]

    # --- Generator methods ---
    def _generateInstance(self, path: str) -> Instance:
        """
        Generator method for Instance instances. 
        Only override for custom instances (e.g., see DataSorter).
        """
        return Instance(path)

    def _generateInstanceData(self, instance: Instance, path: str, dtype: DataType) -> InstanceData:
        """
        Generator method for InstanceData.
        You won't override this!
        """
        return InstanceData(path, dtype)

    # --- task method ---
    def task(self) -> None:
        # NOTE: In any implementing sub-class, you may not override this task method without calling super().task()!
        # Instead, use the helper methods (e.g. self.addDicomCT()) to add data.
        # The DataImporter base module takes care of generating instances of the Instance, InstanceData classes and of linking them correctly to the central data handler.
        # Instances are separated by it's ref attribute.

        # create data instances based on the sorted output
        instances: Dict[str, Instance] = {}
        datas: List[InstanceData] = []
        for idef in self._import_paths:

            # create instances
            if idef.ref not in instances:

                # resolve instance path (same as self.resolvePath but for the instance instead of an instance's file and relative to the config's base instead of absolut)
                ipath = []
                if self.basePath: ipath.append(self.basePath)
                if idef.ref: ipath.append(idef.ref)
                ipath = os.path.join(*ipath)

                # generate instance
                instances[idef.ref] = self._generateInstance(ipath)

                # add the ref as attribute to every instance 
                instances[idef.ref].attr['ref'] = idef.ref

                # adding variable instance attributes
                # TODO: this is experimental atm
                for attr_key, attr_val, attr_ref in self._import_attrs:
                    if attr_ref == idef.ref:
                        instances[idef.ref].attr[attr_key] = attr_val

            # TODO:
            # handle absolute idef.path paths (which should be an option to the user!)
            # NOTE: checks in helper methods will fail if used with relative paths so...

            # adding data to instances
            dtype = DataType(idef.ftype, idef.meta)
            data = self._generateInstanceData(instances[idef.ref], idef.path, dtype)
            instances[idef.ref].addData(data)

            # collect data for later confirmation
            datas.append(data)

        # update instances to the global data handler
        self.config.data.instances = list(instances.values())

        # confirm data
        #   (data.abspath will only resolve once instances are added to the global data handler)
        for data in datas:
            if os.path.exists(data.abspath):
                data.confirm()

