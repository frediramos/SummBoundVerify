from pathlib import Path

from pycparser import c_generator
from pycparser.c_ast import ID, FuncDef, FileAST, FuncCall, Compound

from summboundverify.api import macros, type_stubs, required_stubs, sra_stubs
from summboundverify.utils.visitors import FuncCallsVisitor

from .utils import *
from .generator import Generator
from .parser import FunctionParser
from .api import halt_all, save_current_state


from .test import TestGen
from .test.args.visitors.structs import StructVisitor


class ValidationGenerator(Generator):
    def __init__(
        self,
        concrete_file: str | Path | None,
        summary_file: str | Path | None,
        outputfile: str | Path,
        *,
        arraysize=[5],
        nullbytes=[],

        maxnum=[],
        maxnames=[],

        default={},
        concrete_arrays={},

        pointersize=5,
        fuel=5,

        cncrt_name: str | None = None,
        summ_name: str | None = None,

        memory=False,
        no_api=False,
    ):
        super().__init__(outputfile, concrete_file, summary_file)
        self.arraysize = arraysize
        self.nullbytes = nullbytes
        self.maxnum = maxnum
        self.maxnames = maxnames
        self.default = default
        self.concrete_arrays = concrete_arrays
        self.pointersize = pointersize
        self.fuel = fuel
        self.memory = memory
        self.summ_name = summ_name
        self.cncrt_name = cncrt_name
        self.no_api = no_api

    def get_api_calls(self, funcs):
        api_calls = set()

        complete_api = sra_stubs()
        required_api = required_stubs()

        for i, func in enumerate(funcs, 1):
            visitor = FuncCallsVisitor()
            visitor.visit(func)

            called = visitor.fcalls()

            if i == len(funcs) and not called:
                called = complete_api

            api_calls.update(
                c for c in called
                if c in complete_api and c not in required_api
            )

        validation_defs = list(required_api.values())
        api_defs = [
            complete_api[call]
            for call in api_calls
        ]

        return sorted(validation_defs + api_defs)

    # Gen headers
    # Typedefs, API stubs and Macros
    def gen_headers(self, defs):

        # Add macros and typedefs
        headers = [macros(), *type_stubs(), '']

        # Add API calls
        if not self.no_api:
            headers += self.get_api_calls(defs)
            headers.append('')

        # Add macros
        headers.append(define_macro(POINTER_SIZE_MACRO, self.pointersize))
        headers.append(define_macro(FUEL_MACRO, self.fuel))

        headers += self.gen_macros(ARRAY_SIZE_MACRO, self.arraysize)
        headers += self.gen_macros(MAX_MACRO, self.maxnum)

        return headers

    def gen_macros(self, macro, values=[]):
        macros = []
        for i, v in enumerate(values):

            if isinstance(v, list):
                stringlst = []

                for x, y in enumerate(v):
                    name = f'{macro}_{i+1}_VAR{x+1}'
                    stringlst.append(define_macro(name, y))
                string = ''.join(stringlst)

            else:
                name = f'{macro}_{i+1}'
                string = define_macro(name, v)

            macros.append(string)

        return macros

    # Generate the tests code
    def gen_tests(self, args, ret_type):

        test_defs = []
        main_body = []

        # Number of tests
        tests = max(len(self.maxnum), len(self.arraysize))

        # Save Multiple fresh states if needed (multiple tests)
        main_body += [
            save_current_state(f'fresh_state{i}')
            for i in range(1, tests)
        ]

        for i in range(1, tests+1):
            testName = f'test_{i}'

            # Gen test code
            testCode = self.gen_test(testName, args, ret_type, i)
            test_defs.append(testCode)

            # Call test function from main
            main_body.append(FuncCall(ID(testName), ExprList([])))

            # Halt to a fresh state in between tests
            if i < tests:
                main_body.append(halt_all(f'fresh_state{i}'))

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

    def gen_test(self, testname, args, ret_type, id):

        array_size = self.get_array_size(id)
        null_bytes = self.get_null_byte(id)
        default = self.get_dict_value(id, self.default)
        concrete = self.get_dict_value(id, self.concrete_arrays)

        # Select Macro id for Max value
        max_value = f'{MAX_MACRO}_{id}' if id <= len(self.maxnum) else None

        assert self.cncrt_name is not None
        assert self.summ_name is not None

        # Call Gen visitor
        gen = TestGen(
            args, ret_type,
            self.cncrt_name, self.summ_name,
            self.memory, self.maxnames
        )

        return gen.create_test(
            testname,
            array_size, null_bytes,
            max_value, default,
            concrete, id
        )

    # Generate summary validation test
    def gen(self):

        fparser = FunctionParser(self.tmp_concrete, self.tmp_summary)

        parsed = fparser.parse(
            self.cncrt_name,
            self.summ_name
        )

        self.cncrt_name = parsed.concrete_name
        self.summ_name = parsed.summary_name

        function_defs = [
            f.definition if f else None
            for f in parsed.functions
        ]
        args = parsed.arguments
        ret_type = parsed.return_type

        header = self.gen_headers(function_defs)

        # If one the functions is not provided
        if None in function_defs:
            function_defs.remove(None)

        # Main function to run the tests
        main = create_function(name='main', args=None, returnType='int')

        # Struct builder functions (if exist)
        structs = StructVisitor(self.tmp_concrete).symbolic_structs()
        structs += StructVisitor(self.tmp_summary).symbolic_structs()

        # Gen test definitions and calls from main
        test_defs, main_body = self.gen_tests(args, ret_type)

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
