"""
-------------------------------------------------
MHub - Query data types
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (19.06.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import List, Dict, Any
from mhubio.core import Module, Instance, InstanceData, IO
from mhubio.modules.organizer.DataOrganizer import DataOrganizer
from mhubio.core.RunnerOutput import RunnerOutputType, ClassOutput, ValueOutput
import json, csv, os

@IO.Config('format', str, 'compact', the='format of the report (separated|nested|compact)')
@IO.Config('includes', List[Dict[str, Any]], [], the='list of data types to include in the report')
class ReportExporter(Module):

    format: str
    includes: List[Dict[str, Any]]

    def task(self):
        if True:
            self.generateInstanceReport()
        else:
            self.generateInstancesReport()

    def generateInstancesReport(self):
        pass

    @IO.Instance()
    @IO.Output('out_data', 'report.json', 'json:mod=report', bundle='reports', the='report collecting generated and collected instance data')
    def generateInstanceReport(self, instance: Instance, out_data: InstanceData):
        
        report = []

        # generate the report
        for include in self.includes:

            # generate label / value pair
            label = include['label']
            value = None    

            # extract value based on include directive
            try:
                if 'static' in include:
                    value = include['value']

                elif 'attr' in include and include['attr'] in instance.attr:
                    value = instance.attr[include['attr']]

                elif 'files' in include:
                    files = instance.data.asList() if include['files'] is None else instance.data.filter(include['files']) 

                    aggregate = include['aggregate'] if 'aggregate' in include else 'list'
                    assert aggregate in ['list', 'count']

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

                elif 'data':

                    # fetch the data
                    data = [d for d in instance.outputData if d.name == include['data']]
                    assert len(data) == 1, "data name not unique."
                    data = data[0]
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
                print("Error while generating report for ", include)

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

        # export report
        with open(out_data.abspath, 'w') as f:
            json.dump(report, f, indent=4)

        

        
