from pycparser import c_generator
from pycparser.c_ast import *

from .c_generator import CGenerator
from .utils import *
from .api_gen import api, API_Gen
from .function_parser import FunctionParser
from .test_gen import TestGen
from .test_gen.arg_gen.visitors.structs import StructVisitor


class ValidationGenerator(CGenerator):
    def __init__(self, concrete_file, summary_file,
                 outputfile,
                 arraysize=[5], nullbytes=[],
                 maxnum=[], maxnames=[],
                 default={}, concrete_arrays={},
                 pointersize=5, fuel=5,
                 memory=False,
                 cncrt_name=None, summ_name=None, no_api=False,
                 fakelib=None):

        super().__init__(outputfile, concrete_file, summary_file, fakelib)

        self.arraysize = arraysize
        self.nullbytes = nullbytes
        self.maxnum = maxnum
        self.maxnames = maxnames
        self.default = default
        self.concrete_arrays = concrete_arrays
        self.pointersize = pointersize
        self.fuel = fuel

        self.memory = memory

        # Summary name (if summ is not isolated in a file, e,g in a library)
        self.summ_name = summ_name
        self.cncrt_name = cncrt_name

        self.no_api = no_api

    # Gen headers
    # Typedefs, API stubs and Macros

    def gen_headers(self, defs):
        _, summ_def = defs

        # Add core api functions
        headers = [*api.type_defs]

        if not self.no_api:
            headers += sorted(api.validation_api.values())
            headers.append('\n')

            # Visitor to get all function calls
            call_vis = FCallsVisitor()
            call_vis.visit(summ_def)
            calls = call_vis.fcalls()

            # Summary code is not provided
            if not calls:
                calls = api.all_api.keys()

            # Check if calls are api functions
            # Only add stubs for functions not already added by API.validation_api
            calls = filter(lambda x: x in api.all_api.keys(), calls)
            calls = filter(lambda x: x not in api.validation_api, calls)

            headers += [api.all_api[c] for c in sorted(calls)]
            headers.append('\n')

        # Macros
        headers += defineMacro(POINTER_SIZE_MACRO, self.pointersize)
        headers += defineMacro(FUEL_MACRO, self.fuel)
        headers += self.genMacros(ARRAY_SIZE_MACRO, self.arraysize)
        headers += self.genMacros(MAX_MACRO, self.maxnum)

        return headers

    def genMacros(self, macro, values=[]):
        macros = []
        for i, v in enumerate(values):

            if isinstance(v, list):
                stringlst = []

                for x, y in enumerate(v):
                    name = f'{macro}_{i+1}_VAR{x+1}'
                    stringlst.append(defineMacro(name, y))
                string = ''.join(stringlst)

            else:
                name = f'{macro}_{i+1}'
                string = defineMacro(name, v)

            macros.append(string)

        return macros

    # Generate the tests code

    def genTests(self, args, ret_type):

        test_defs = []
        main_body = []

        # Number of tests
        tests = max(len(self.maxnum), len(self.arraysize))

        # Save Multiple fresh states if needed (multiple tests)
        main_body += [API_Gen().save_current_state(f'fresh_state{i}')
                      for i in range(1, tests)]

        for i in range(1, tests+1):
            testName = f'test_{i}'

            # Gen test code
            testCode = self.genTest(testName, args, ret_type, i)
            test_defs.append(testCode)

            # Call test function from main
            main_body.append(FuncCall(ID(testName), ExprList([])))

            # Halt to a fresh state in between tests
            if i < tests:
                main_body.append(API_Gen().halt_all(f'fresh_state{i}'))

        return test_defs, main_body

    def get_array_size(self, id):

        if isinstance(self.arraysize[id-1], list):
            array_size = []
            for x, _ in enumerate(self.arraysize[id-1]):
                name = f'{ARRAY_SIZE_MACRO}_{id}_VAR{x+1}'
                array_size.append(name)

        else:
            arrId = min(id, len(self.arraysize))
            array_size = f'{ARRAY_SIZE_MACRO}_{arrId}'

        return array_size

    def get_null_byte(self, id):
        if self.nullbytes:

            if id <= len(self.nullbytes):
                position = self.nullbytes[id-1]
            else:
                position = self.nullbytes[-1]

            if isinstance(position, list):
                null_byte = []
                for x in position:
                    null_byte.append(x)
            else:
                null_byte = position

            return null_byte

        else:
            return self.nullbytes

    def get_dict_value(self, id, dict):
        if dict:
            if id <= len(dict):
                return dict[id-1]
            else:
                return dict[-1]
        else:
            return dict

    def genTest(self, testname, args, ret_type, id):

        array_size = self.get_array_size(id)
        null_bytes = self.get_null_byte(id)
        default = self.get_dict_value(id, self.default)
        concrete = self.get_dict_value(id, self.concrete_arrays)

        # Select Macro id for Max value
        max_value = f'{MAX_MACRO}_{id}' if id <= len(self.maxnum) else None

        # Call Gen visitor
        gen = TestGen(args, ret_type,
                      self.cncrt_name, self.summ_name,
                      self.memory, self.maxnames)

        return gen.createTest(testname,
                              array_size, null_bytes,
                              max_value, default, concrete, id)

    # Generate summary validation test

    def gen(self):
        try:

            fparser = FunctionParser(self.tmp_concrete, self.tmp_summary)

            cname, sname, \
                function_defs, args, \
                ret_type = fparser.parse(self.cncrt_name, self.summ_name)

            self.cncrt_name = cname
            self.summ_name = sname

            header = self.gen_headers(function_defs)

            # If one the functions is not provided
            if None in function_defs:
                function_defs.remove(None)

            # Main function to run the tests
            main = createFunction(name='main', args=None, returnType='int')

            # Struct builder functions (if exist)
            structs = StructVisitor(self.tmp_concrete).symbolic_structs()
            structs += StructVisitor(self.tmp_summary).symbolic_structs()

            # Gen test definitions and calls from main
            test_defs, main_body = self.genTests(args, ret_type)

            # Create main() body
            block = Compound(main_body)
            main_ast = FuncDef(main, None, block, None)

            gen_ast = FileAST(structs + function_defs + test_defs)
            gen_ast.ext.append(main_ast)

            # Generate string from ast
            generator = c_generator.CGenerator()
            generated_string = generator.visit(gen_ast)

            self.write_to_file(generated_string.rstrip(), header)
            self.remove_files(self.tmp_concrete, self.tmp_summary)
            return self.outputfile

        except Exception as e:
            self.remove_files(self.tmp_concrete, self.tmp_summary)
            raise e
