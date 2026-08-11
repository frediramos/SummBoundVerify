from copy import deepcopy
from pathlib import Path

from pycparser import c_generator
from pycparser.c_ast import (
    ID,
    Return,
    FuncDef,
    FileAST,
    FuncCall,
    Compound,
    Constant,
    TypeDecl,
)

from .utils import *
from .utils.visitors import FuncCallsVisitor

from .generator import Generator
from .function_parser import FunctionParser

from .api_gen import (
    halt_all,
    save_current_state,
    type_defs,
    complete_api,
    validation_api,
)

from .test_gen import TestGen
from .test_gen.arg_gen.visitors.structs import StructVisitor


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
        engine: str = 'se',
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
        self.engine = engine

    def get_api_calls(self, funcs):
        fdefs = []
        fcalls = set()

        # Always include the validation API
        fdefs += sorted(validation_api.values())
        fdefs.append('')

        for i, func in enumerate(funcs, 1):

            # Visit and fetch all function calls
            visitor = FuncCallsVisitor()
            visitor.visit(func)
            called = visitor.fcalls()

            if not called and i == len(funcs):
                called = complete_api.keys()

            # Filter non API functions
            called = filter(lambda x: x in complete_api.keys(), called)

            # Filter functions already included with the validation API
            called = filter(lambda x: x not in validation_api, called)

            fcalls.update(called)

        fdefs += [complete_api[c] for c in sorted(fcalls)]

        return fdefs

    def gen_summary_prototype(self, defs):
        """Declare the summary before the test body calls it.

        The summary is a separate translation unit, so without a declaration
        the call goes through an implicit `int`-returning declaration and a
        wider return value is silently truncated. Symbolically that is
        invisible (the test is built for a 32-bit target, where it happens to
        be a no-op) but a native build reports it as a divergence between the
        summary and the concrete function -- a harness artefact that looks
        exactly like a real finding.
        """
        def find(name):
            return next(
                (d for d in defs if d is not None and d.decl.name == name),
                None
            )

        summ_def = find(self.summ_name)

        if summ_def is not None:
            decl = summ_def.decl

        else:
            # Only `-summ` gives us the summary's AST; with `--lib` we know
            # nothing but its name. Fall back to the concrete function's
            # signature, which is the premise of the comparison anyway.
            cncrt_def = find(self.cncrt_name)
            if cncrt_def is None:
                return []

            decl = deepcopy(cncrt_def.decl)
            decl.name = self.summ_name

            inner = decl.type
            while not isinstance(inner, TypeDecl):
                inner = inner.type
            inner.declname = self.summ_name

        generator = c_generator.CGenerator()
        return [f'extern {generator.visit(decl)};', '']

    # Gen headers
    # Typedefs, API stubs and Macros
    def gen_headers(self, defs):

        if self.engine == 'fuzz':
            headers = self.gen_summary_prototype(defs)

        else:
            # Add core api functions.
            headers = list(type_defs)
            headers.append('')

            # Add API calls
            if not self.no_api:
                headers += self.get_api_calls(defs)
                headers.append('')

        # Add macros
        headers.append(defineMacro(POINTER_SIZE_MACRO, self.pointersize))
        headers.append(defineMacro(FUEL_MACRO, self.fuel))

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
        main_body += [
            save_current_state(f'fresh_state{i}')
            for i in range(1, tests)
        ]

        for i in range(1, tests+1):
            testName = f'test_{i}'

            # Gen test code
            testCode = self.genTest(testName, args, ret_type, i)
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

    def genTest(self, testname, args, ret_type, id):
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
        test_defs, main_body = self.genTests(args, ret_type)

        # main() is declared int, so it has to return one: without this the
        # fuzz build warns on every single compile, and a harness that always
        # warns is a harness whose warnings stop being read.
        main_body.append(Return(Constant('int', '0')))

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
