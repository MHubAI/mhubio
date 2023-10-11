"""
-------------------------------------------------
MHub - Query data types
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (19.06.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from enum import Enum
from typing import List, Dict, Any
from mhubio.core import Module, Instance, InstanceData, DataType, Meta, IO, DataTypeQuery
from mhubio.core.Logger import MLogLevel
from mhubio.modules.organizer.DataOrganizer import DataOrganizer
from mhubio.core.RunnerOutput import ClassOutput, ValueOutput
import json, csv, os

class ReportFormat(str, Enum):
    COMPACT = 'compact'
    NESTED = 'nested'
    SEPARATED = 'separated'

@IO.Config('globalreport', bool, False, the='flag to indicate whether to generate a global report or a report for each instance')
@IO.Config('format', ReportFormat, 'compact', factory=ReportFormat, the='format of the report (separated|nested|compact)')
@IO.Config('includes', List[Dict[str, Any]], [], the='list of data types to include in the report')
@IO.Config('meta', dict, {'mod': 'report'}, the="additional meta data attached to report")
@IO.Config('csv', bool, False, the="experimental flag to export the compact global report as csv instead of json.")
class ReportExporter(Module):

    globalreport: bool
    format: ReportFormat
    meta: dict
    csv: bool
    includes: List[Dict[str, Any]]

    def task(self):
        if not self.globalreport:
            self.task_instance()
        else:
            self.task_instances()

    @IO.Instance()
    @IO.Output('out_data', 'report.json', 'json:mod=report', bundle='reports', the='report collecting generated and collected instance data')
    def task_instance(self, instance: Instance, out_data: InstanceData):
        
        # generate report
        report = self.generateInstanceReport(instance, format=self.format)

        # extend metadata
        assert isinstance(self.meta, dict)
        out_data.type.meta += self.meta

        # export report
        with open(out_data.abspath, 'w') as f:
            json.dump(report, f, indent=4)

        
    def task_instances(self):
        
        # create output data and append to global instance
        global_instance = self.config.data.globalInstance
        reports_bundle = global_instance.getDataBundle('reports')

        ext = 'csv' if self.csv else 'json'
        out_data = InstanceData('report.' + ext, 
                                DataType.fromString(ext + ':mod=report'),
                                instance=global_instance, 
                                bundle=reports_bundle, 
                                auto_increment=True)
        
        # extend meta
        assert isinstance(self.meta, dict)
        out_data.type.meta += self.meta

        # create bundle path
        self.log("Creating bundle path: ", out_data.abspath, level=MLogLevel.DEBUG)
        out_data.dc.makedirs()

        # collect report
        report = []

        try:

            # generate report for all instances 
            for instance in self.config.data.instances:
                instance_report = self.generateInstanceReport(instance, format=ReportFormat.COMPACT)
                report.append(instance_report)

            # export report
            if not self.csv:
                with open(out_data.abspath, 'w') as f:
                    json.dump(report, f, indent=4)
            else:
                import pandas as pd
                df = pd.DataFrame(report)
                df.to_csv(out_data.abspath, index=False)

        except Exception as e:
            self.log("Error while generating global report: ", str(e), level=MLogLevel.ERROR)

        # confirm output data
        if os.path.exists(out_data.abspath):
            out_data.confirm()
            

    def generateInstanceReport(self, instance: Instance, format: ReportFormat = ReportFormat.COMPACT):
        
        report = []

        # generate the report
        for include in self.includes:

            # generate label / value pair
            label = include['label']
            value = None    

            # extract value based on include directive
            # TODO: we may check that 'static', 'attr', 'files', 'data', 'meta' actually is the FIRST key of the include dict
            try:
                if 'static' in include:
                    value = include['value']

                elif 'attr' in include and include['attr'] in instance.attr:
                    value = instance.attr[include['attr']]

                elif 'files' in include:
                    files = instance.data if include['files'] is None else instance.data.filter(include['files']) 

                    aggregate = include['aggregate'] if 'aggregate' in include else 'list'
                    assert aggregate in ['list', 'count', 'first']

                    # extract a list or a count
                    if aggregate == 'list':
                        pattern =   include['pattern'] if 'pattern' in include else '[filename]'
                        delimiter = include['delimiter'] if 'delimiter' in include else None

                        values_list = []
                        for file in files:
                            file_value = DataOrganizer.resolveTarget(pattern, file)
                            if file_value is not None:
                                values_list.append(file_value)

                        value = delimiter.join(values_list) if delimiter is not None and isinstance(delimiter, str) else values_list

                    elif aggregate == 'count':
                        value = len(files)

                    elif aggregate == 'first':
                        file = files.ask(0)
                        assert 'pattern' in include, "Pattern must be specified."
                        pattern = include['pattern']
                        assert file is not None, "No file found for include directive."
                        value = DataOrganizer.resolveTarget(pattern, file)

                elif 'data':

                    # fetch the data
                    data = instance.outputData.filter(include['data'])

                    # query must be specific enough to identify a single output data object
                    assert len(data) == 1, "data name not unique."
                    data = data.get(0)

                    # output data object must be an instacne of value output or class output 
                    assert isinstance(data, ValueOutput) or isinstance(data, ClassOutput)

                    # extract description, value or class probability
                    if include['value'] == 'description' and 'class' not in include:
                        value = data.description

                    elif include['value'] == 'label' and 'class' not in include:
                        value = data.label

                    elif include['value'] == 'value' and 'class' not in include:
                        value = data.value

                    elif include['value'] == 'type':
                        assert isinstance(data, ValueOutput), "type attribute only available for value outputs."
                        if data.dtype == float: value = "float"
                        elif data.dtype == int: value = "int"
                        elif data.dtype == str: value = "str"
                        elif data.dtype == bool: value = "bool"
                        else: value = str(data.dtype)

                    elif include['value'] == 'description' and 'class' in include:
                        assert isinstance(data, ClassOutput), "only use the class attribute on class prediction output types."
                        value = data[include['class']].description

                    elif include['value'] == 'label' and 'class' in include:
                        assert isinstance(data, ClassOutput), "only use the class attribute on class prediction output types."
                        value = data[include['class']].label

                    elif include['value'] in ['value', 'probability'] and 'class' in include:
                        assert isinstance(data, ClassOutput), "only use the class attribute on class prediction output types."
                        value = data[include['class']].probability
                    
                # break if no value was generated
                assert value is not None

                # append entry to report
                report.append({
                    'label': label,
                    'value': value
                })

            # report errors
            except Exception as e:
                self.log("Error while generating report for ", include, ": ", str(e), level=MLogLevel.ERROR)

        # compact
        if self.format == 'compact':
            report = {r['label']: r['value'] for r in report}

        # nested
        if self.format == 'nested':
            nested_report = {}
            for (label, value) in [(r['label'], r['value']) for r in report]:
                _report = nested_report
                path = label.split('/')
                for i, p in enumerate(path): 
                    v = {"value": value} if i == len(path) - 1 else {}
                    _report = _report.setdefault(p.strip(), v)
            report = nested_report

        # return json
        return report
