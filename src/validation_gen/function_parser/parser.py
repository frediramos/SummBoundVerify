from ..test_gen.arg_gen import Symbolic_Args

from ..utils import utils

from .fexception import FunctionException
from .visitors import FunctionVisitor, ReturnTypeVisior


class FunctionParser():

    def getFunctions(self, file: str) -> dict:
        ast = utils.parseFile(file)
        vis = FunctionVisitor(ast, file)
        functions = vis.functions()
        return functions

    def __init__(self, concrete: str, summary: str):

        self.concrete = concrete
        self.summary = summary
        self.concrete_debug = None
        self.summary_debug = None
        self.tmp = 'tmp_'

        self.cnctr_functions = None
        self.summ_functions = None

        if self.concrete:
            self.cnctr_functions = self.getFunctions(self.concrete)
            self.concrete_debug = self.concrete.replace(self.tmp, '')

        if self.summary:
            self.summ_functions = self.getFunctions(self.summary)
            self.summary_debug = self.summary.replace(self.tmp, '')

    # Parse target functions from the given files
    # Returns (ast_defs, ast_args, ret_type)

    def parse(self, cncrt_name, summ_name):
        cncrt_name, summ_name, defs = self.definitions(cncrt_name, summ_name)
        args = self.arguments(defs)
        ret = self.returnType(defs)
        return cncrt_name, summ_name, defs, args, ret

    # Get the target functions ast_def from the functions in the given files
    def definitions(self, cncrt_name: str, summ_name: str):
        cncrt = None
        summ = None

        if self.cnctr_functions:
            cncrt, cncrt_name = self.get_def(
                self.cnctr_functions, cncrt_name, self.concrete, 'Concrete Function')

        if self.summ_functions:
            summ, summ_name = self.get_def(
                self.summ_functions, summ_name, self.summary, 'Summary')

        return [cncrt_name, summ_name, [cncrt, summ]]

    # Get function arguments

    def arguments(self, definitions: list):
        cncrt_def, summ_def = definitions

        cncrt_args = None
        summ_args = None

        if cncrt_def:
            cncrt_args, cncrt_args_def = self.get_args(cncrt_def)

        if summ_def:
            summ_args, _ = self.get_args(summ_def)

        if self.summary and self.concrete\
                and cncrt_args != summ_args:
            message = (
                "Arguments do not match!\n"
                f"Summary path: \'{self.summary_debug}\'\n"
                f"Concrete Function: \'{self.concrete_debug}\'")
            raise FunctionException(message)

        return cncrt_args_def

    # Get return type

    def returnType(self, definitions: list):
        cncrt_def, summ_def = definitions

        ret1 = None
        ret2 = None

        if cncrt_def:
            ret1 = self.get_ret(cncrt_def)

        if summ_def:
            ret2 = self.get_ret(summ_def)

        if not ret1 or not ret2:
            return ret1 if ret1 else ret2

        elif ret1 != ret2:
            message = (
                "Return values do not match!\n"
                f"Summary path: \'{self.summary_debug}\'\n"
                f"Concrete Function: \'{self.concrete_debug}\'")
            raise FunctionException(message)

        return ret1

    def get_ret(self, definition):
        ret = definition.decl.type.type
        ret_vis = ReturnTypeVisior()
        ret_vis.visit(ret)
        ret = ret_vis.get_ret()
        return ret

    def get_args(self, definition):
        args_def = definition.decl.type.args.params if definition.decl.type.args else None
        args_vis = Symbolic_Args(args_def)
        args_type = args_vis.get_types()
        return args_type, args_def

    def get_def(self, functions: dict, fname: str, file: str, ftype: str):
        names = functions.keys()
        definition = None
        message = None

        if file.startswith(self.tmp):
            file = file.lstrip(self.tmp)

        if len(names) == 0:
            message = f"ERROR: No {ftype}(s) provided in: \'{file}\'"
            raise FunctionException(message)

        if fname:
            if fname not in names:
                message = f"ERROR: {ftype} ({fname}) not found in the given file: \'{file}\'"
                raise FunctionException(message)

            else:
                definition = functions[fname]

        else:
            if len(names) == 1:
                definition, = list(functions.values())
                fname, = names
            else:
                message = f"ERROR: If no function name provided\n \
						There should be only one {ftype}\
						to be compared with in \'{file}\'"
                raise FunctionException(message)

        return definition, fname
