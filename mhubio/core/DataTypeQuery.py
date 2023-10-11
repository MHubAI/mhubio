"""
-------------------------------------------------
MHub - Query data types
-------------------------------------------------

-------------------------------------------------
Author: Leonard Nürnberg (19.06.2023)
Email:  leonard.nuernberg@maastrichtuniversity.nl
-------------------------------------------------
"""

from typing import TypeVar, List, Union
from .Meta import Meta
from .DataType import DataType
from .RunnerOutput import RunnerOutput, ValueOutput, ClassOutput
import re

T = TypeVar('T', bound=Union[DataType, RunnerOutput])

class DataTypeQuery:

    """
    NOTE: (B) added to those that are already supported in current implementation using the InstanceDataColelction filter method for datatypes

    List of operations we want to support:
    - EQUAL =               -> meta string equals value
    - NOT EQUAL !=          -> everything except the given value
    - ANY / PLACEHOLDER =*  -> any value (use * as wildcard value here or see it as part of the operator with no value specified)
    - CONTAINS *=           -> meta string contains value (B)
    - SET EQUAL ><          -> only for list values on either side (converts to = for strings), checks if both lists contain teh same values but in arbitrary order
    - CONTAINS ALL >=       -> list: left side list contains all values (or more) from the right side list; str: left side string contains right side string (remove?); num: x >= y
    - CONTAINS ANY <=       -> list: left side list contains at least one value from the right side list but no values not in right side list; num: x <= y
    - CONTAINS NONE <>      -> list: left side list does not contain any value from the right side list; [<>,>>]
    - CONTAINS ONLY <<      -> list: left side list contains only values from the right side list; [><,<<]
    
    - REGEX MATCH =~        -> str: meta string matches regex
    - GREATER THAN >        -> num: x > y
    - LESS THAN <           -> num: x < y

    List of value placeholders / special chaarcters we want to support:
    - ANY / PLACEHOLDER *  -> used as value placeholder
    - OR |                 -> e.g. value1|value2 
    - AND +                -> e.g. value1+value2 (makes no sense for = operator but e.g. for <= operator)
    - LIST ,               -> e.g. value1,value2 (will be treated as a list for list operators -> [value1, value2])


    Chaining queries (and, or, groups)
    - AND _AND_             -> all queries must be true
    - OR  _OR_              -> at least one query must be true

    A+B|C -> (A AND B) OR C
    A|B+C -> A OR (B AND C)

    Query examples:
    - dicom|nrrd:roi=HEART|LIVER                  -> file type is dicom or nrrd and roi is heart or liver
        alternative: dicom:roi=HEART|LIVER OR nrrd:roi=HEART|LIVER
        alternative: dicom:roi=HEART OR dicom:roi=LIVER OR nrrd:roi=HEART OR nrrd:roi=LIVER
        alternative: dicom|nrrd:roi=HEART OR dicom|nrrd:roi=LIVER
    - dicom:roi=HEART OR nrrd:roi=LUNG            -> file type is dicom and roi is heart or file type is nrrd and roi is lung
    - dicom:roi<=HEART,LIVER AND dicom:roi<>BRAIN -> file type is dicom and roi contains heart or liver but not brain. 
                                                    In any AND chain, the second file typoe can be omitted (e.g., :roi<>Brain) as a file can never have more than one file type.
    - any:mod=ct|mr AND any:roi=HEART|LIVER       -> modality is ct or mr and modality is ct or mr and roi is heart or liver on any file type
    """

    query: str

    def __init__(self, query: str) -> None:
        self.query = query

    def exec(self, ref_type: DataType) -> bool:
        return self.parse(self.query, ref_type)

    def filter(self, ref_types: List[T]) -> List[T]:
        matching_types: List[T] = []
        for ref_type in ref_types:
            if self.parse(self.query, ref_type):
                matching_types.append(ref_type)
        return matching_types
    
    @classmethod
    def parse(cls, query: str, ref_type: Union[DataType, RunnerOutput]) -> bool:

        # tokenize query
        tokens = cls.tokenize(query)

        # parse all NOT
        while 'NOT' in tokens:
            # find first NOT
            i_not = tokens.index('NOT')

            # find left and right side
            right = tokens[i_not+1]

            # resolve left and right side
            resolved = ['FALSE', 'TRUE'][not cls.evaluate(right, ref_type)]
            tokens = tokens[:i_not] + [resolved] + tokens[i_not+2:]

        # parse all AND 
        while 'AND' in tokens:
            # find first AND
            i_and = tokens.index('AND')

            # find left and right side
            left = tokens[i_and-1]
            right = tokens[i_and+1]

            # resolve left and right side
            resolved = ['FALSE', 'TRUE'][cls.evaluate(left, ref_type) and cls.evaluate(right, ref_type)]
            tokens = tokens[:i_and-1] + [resolved] + tokens[i_and+2:]

        # parse all OR
        while 'OR' in tokens:
            # find first OR
            i_or = tokens.index('OR')

            # find left and right side
            left = tokens[i_or-1]
            right = tokens[i_or+1]

            # resolve left and right side
            resolved = ['FALSE', 'TRUE'][cls.evaluate(left, ref_type) or cls.evaluate(right, ref_type)]
            tokens = tokens[:i_or-1] + [resolved] + tokens[i_or+2:]

        # if there is only one token left, it must be the result
        assert len(tokens) == 1
        return cls.evaluate(tokens[0], ref_type)

    @classmethod
    def tokenize(cls, query: str) -> List[str]:
        group_level = 0
        tokens = ['']

        for c in query:
            if c == '(':
                group_level += 1

            elif c == ')':
                group_level -= 1

            elif c == ' ':
                if group_level == 0:
                    tokens.append('')
                    continue

            tokens[len(tokens)-1] += c

        return tokens

    @classmethod
    def evaluate(cls, expr: str, ref_type: Union[DataType, RunnerOutput]) -> bool:

        # check value is already fully resolced and evaluated
        if expr == 'TRUE':
            return True
        
        elif expr == 'FALSE':
            return False

        # check if definiton is a group
        if expr.startswith('(') and expr.endswith(')'):
            return cls.parse(expr[1:-1], ref_type)

        # evaluate single expression
        ftype_def, *metas_def = expr.split(':')

        # reference meta 
        #  we use empty meta if meta is None as Meta is optional for RunnerOutput instances
        ref_meta = ref_type.meta or Meta()

        # type matching
        if isinstance(ref_type, DataType): # ftype_def -> | separated list of file types
            if not str(ref_type.ftype.value).lower() in ftype_def.lower().split('|') and ftype_def.lower() != 'any':
                return False
            
        elif isinstance(ref_type, RunnerOutput): # ftype_def -> | separated list of data names (identifyers)
            if not str(ref_type.name).lower() in ftype_def.lower().split('|') and ftype_def.lower() != 'any':
                return False

            # enhance 
            ref_meta += {
                '.name': ref_type.name,
                '.label': ref_type.label,
                '.description': ref_type.description
            }

            if isinstance(ref_type, ValueOutput):
                ref_meta += {
                    '.dtype': ref_type.dtype,
                    '.value': ref_type.value
                }

            elif isinstance(ref_type, ClassOutput) and ref_type.value is not None:
                #'.classes.label': [c.label for c in ref_type.classes],
                #'.classes.probability': [c.probability for c in ref_type.classes],
                #'.classes.description': [c.description for c in ref_type.classes],
                ref_meta += {
                    '.value': ref_type.value
                }

        # meta matching
        return all(cls.evaluateMeta(md, ref_meta) for md in metas_def)
        
    @classmethod
    def evaluateMeta(cls, kov: str, ref_meta: Meta, verbose: bool = False) -> bool:
        """
        - EQUAL =               -> meta string equals value
        - NOT EQUAL !=          -> everything except the given value
        - SET EQUAL ><          -> only for list values on either side (converts to = for strings), checks if both lists contain teh same values but in arbitrary order
        - CONTAINS ALL >=       -> list: left side list contains all values (or more) from the right side list; str: left side string contains right side string (remove?); num: x >= y
        - CONTAINS ANY <=       -> list: left side list contains at least one value from the right side list but no values not in right side list; num: x <= y
        - CONTAINS NONE <>      -> list: left side list does not contain any value from the right side list; [<>,>>]

        - REGEX MATCH ~=        -> str: meta string matches regex
        - GREATER THAN >        -> num: x > y
        - LESS THAN <           -> num: x < y 
        """

        if verbose:
            print("checking: ", kov, " against ", ref_meta, '=' in kov)

        if '!=' in kov:
            k, v = kov.split('!=')
            return k not in ref_meta or ref_meta[k] != v
               
        elif '><' in kov:
            k, v = kov.split('><')
            
            # return false if key is not present in reference meta
            if not k in ref_meta:
                return False

            # require either side to be a list for this operator TODO: revisit.
            assert ',' in v and ',' in ref_meta[k]

            v_lst = v.split(',')
            r_lst = ref_meta[k].split(',')
            return set(v_lst) == set(r_lst)
        
        elif '>=' in kov: # supports list, str, num
            k, v = kov.split('!=')
            
            # return false if key is not present in reference meta
            if not k in ref_meta:
                return False
            
            # evaluation depends on the query datatyoe (supports list, str, num)
            # TODO: should we throw an error if v is not a string?
            if v.isnumeric(): # number
                return int(ref_meta[k]) >= int(v)
            elif ',' in v: # list
                v_lst = v.split(',')
                r_lst = ref_meta[k].split(',')
                return set(v_lst) <= set(r_lst)
            else: # string
                return v in ref_meta[k]
            
        elif '<=' in kov: # supports list,  num
            k, v = kov.split('<=')

            if verbose:
                print(f"k: {k}, v: {v}, o: <=")

            # return false if key is not present in reference meta
            if not k in ref_meta:
                if verbose: print(f"key {k} not in reference meta")
                return False
            
            # evaluation depends on the query datatyoe (supports list, num)
            # TODO: should we raise an error if v is not a list?
            if v.isnumeric(): # number
                if verbose: print(f"v is numeric. Comparing {ref_meta[k]} <= {v}: {int(ref_meta[k]) <= int(v)}")
                return int(ref_meta[k]) <= int(v)
            else: # list
                v_lst = v.split(',')
                r_lst = ref_meta[k].split(',')
                if verbose: print(f"v is list. Comparing {v_lst} <= {r_lst}: {set(v_lst) <= set(r_lst)}")
                return set(v_lst) >= set(r_lst) and len(r_lst) > 0
            
        elif '<>' in kov: # supports list
            k, v = kov.split('<>')

            # return false if key is not present in reference meta
            if not k in ref_meta:
                return False
            
            # require either side to be a list for this operator TODO: revisit.
            assert ',' in v and ',' in ref_meta[k]

            v_lst = v.split(',')
            r_lst = ref_meta[k].split(',')

            return len(set(v_lst) & set(r_lst)) == 0
        
        elif '~=' in kov: # supports str
            k, v = kov.split('~=')

            # return false if key is not present in reference meta
            if not k in ref_meta:
                return False
            
            # evaluate regular expression
            if verbose: print("regex match: ", v, " against ", ref_meta[k])
            return re.match(v, ref_meta[k]) is not None
        
        elif '=' in kov:
            k, v = kov.split('=')

            # debug
            if verbose: 
                print(f"k: {k}, v: {v}, o: =")
            
            # return false if key is not present in reference meta
            if not k in ref_meta:
                if verbose: print(f"key {k} not in reference meta")
                return False
            
            # placeholder (we already checked that the key exists in reference meta, so any value is valid)
            if v == '*':
                return True

            # compare value against all options
            for v_option in v.split('|'):
                if ref_meta[k].lower() == v_option.lower():
                    return True
            return False

        elif '>' in kov: # supports num
            k, v = kov.split('>')

            # return false if key is not present in reference meta
            if not k in ref_meta:
                return False
            
            # requires both sides to be numbers
            # TODO: revisit and should we test v earlier (befor k in ref_meta check)?
            assert v.isnumeric() and str(ref_meta[k]).isnumeric()
        
            return int(ref_meta[k]) > int(v)
        
        elif '<' in kov: # supports num
            k, v = kov.split('<')

            # return false if key is not present in reference meta
            if not k in ref_meta:
                return False
            
            # requires both sides to be numbers
            # TODO: revisit and should we test v earlier (befor k in ref_meta check)?
            assert v.isnumeric() and str(ref_meta[k]).isnumeric()

            return int(ref_meta[k]) < int(v)


        else:
            raise Exception("Invalid operator in key operator value string")


    def __str__(self):
        return self.query