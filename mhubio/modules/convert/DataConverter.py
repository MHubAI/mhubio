"""
-------------------------------------------------
MHub - Conversion Base Module
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import Optional, List
from mhubio.Config import Module, Instance, InstanceData, DataType, FileType

class DataConverter(Module):
    """
    Conversion module. 
    Convert instance data from one to another datatype without modifying the data.
    """

    def convert(self, instance: Instance) -> Optional[InstanceData]:
        print("Ooops, not implemented.")
        return None

    def task(self):
        # get instances
        # instances = self.config.data.getInstances(True, DataType(FileType.DICOM))
        # assert len(instances) > 0
        instances = self.config.data.instances

        # execute convert for each instance
        # TODO: add parallelization
        for instance in instances:
            converted = self.convert(instance)

            if converted is not None:
                instance.addData(converted)


class BundleDataConverter(Module):

    def getInstances(self) -> List[Instance]:
        return self.config.data.instances

    def getInData(self, instance: Instance) -> Optional[InstanceData]:
        print("Ooops, not implemented.")
        return None
    
    def getOutData(self, in_data: InstanceData) -> Optional[InstanceData]:
        print("Ooops, not implemented.")
        return None

    def convert(self, in_data: InstanceData, out_data: InstanceData) -> None:
        print("Ooops, not implemented.")
        return None
    
    def getRef(self) -> str:
        return self.__class__.__name__
    
    def task(self):
        # get instances
        instances = self.getInstances()

        # execute convert for each instance
        for instance in instances:

            # get data
            if (in_data := self.getInData(instance)) is None:
                continue 

            # get out data
            if (out_data := self.getOutData(in_data)) is None:
                continue 

            # create bundle
            bundle = in_data.getDataBundle(ref=self.getRef())

            # set bundle to data (but not yet data to bundle) to make abspath work
            out_data.bundle = bundle

            # convert data
            self.convert(in_data, out_data)
            
            # add data
            bundle.addData(out_data)