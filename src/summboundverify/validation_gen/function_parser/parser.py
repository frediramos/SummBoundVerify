from pathlib import Path

from summboundverify.exceptions import (
    ArgumentMismatchError,
    MissingFunctionError,
    ReturnMismatchError,
    MultipleFunctionsError,
)

from summboundverify.utils.summary import FunctionType

from .visitors import FunctionVisitor, ReturnTypeVisior, Function

from ..test_gen.arg_gen import Symbolic_Args
from ..utils import parse_file


class FunctionParser():

    def __init__(self, concrete: str | Path | None, summary: str | Path | None):

        self.concrete = Path(concrete) if concrete else None
        self.summary = Path(summary) if summary else None

        self.cnctr_functions = None
        self.summ_functions = None

        if self.concrete:
            self.cnctr_functions = self.get_functions(self.concrete)

        if self.summary:
            self.summ_functions = self.get_functions(self.summary)

    def get_functions(self, file: str | Path):
        ast = parse_file(str(file))
        vis = FunctionVisitor(ast, file)
        functions = vis.functions()
        return functions

    # Get the target functions ast_def from the functions in the given files
    def definitions(self, cncrt_name: str | None, summ_name: str | None):
        cnctr_funcs = [None]
        summ_funcs = [None]

        cncrt_entry = None
        summ_entry = None

        if self.cnctr_functions:
            cncrt_name, cncrt_entry, cnctr_funcs = self.get_def(
                self.cnctr_functions,
                cncrt_name,
                self.concrete,  # type: ignore
                FunctionType.concrete
            )

        if self.summ_functions:
            summ_name, summ_entry, summ_funcs = self.get_def(
                self.summ_functions,
                summ_name,
                self.summary,  # type: ignore
                FunctionType.summary
            )

        return [
            cncrt_name, summ_name,
            (cncrt_entry, summ_entry),
            [*cnctr_funcs, *summ_funcs]
        ]

    # Get function arguments
    def arguments(self, entries: list):
        cncrt_def, summ_def = entries

        cncrt_args = []
        summ_args = []

        if cncrt_def:
            cncrt_args, cncrt_args_def = self.get_args(cncrt_def)

        if summ_def:
            summ_args, _ = self.get_args(summ_def)

        if (
            self.summary and
            self.concrete and
            cncrt_args != summ_args
        ):
            raise ArgumentMismatchError(cncrt_args, summ_args)

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
            raise ReturnMismatchError(ret1, ret2)

        return ret1

    def get_ret(self, func: Function):
        ret = func.return_type
        ret_vis = ReturnTypeVisior()
        ret_vis.visit(ret)
        ret = ret_vis.get_ret()
        return ret

    def get_args(self, func: Function):
        args_def = func.args
        args_vis = Symbolic_Args(args_def)
        args_type = args_vis.get_types()
        return args_type, args_def

    def get_def(
        self,
        functions: dict[str, Function],
        fname: str | None,
        file: str | Path,
        ftype: FunctionType
    ):
        file = Path(file)
        names = list(functions.keys())

        if len(names) == 0:
            raise MissingFunctionError(ftype, file)

        if fname:
            if fname not in names:
                raise MissingFunctionError(ftype, file, fname)
            entry = functions[fname]
        else:
            fname = names[-1]
            entry = list(functions.values())[-1]

        defs = list(functions.values())

        return fname, entry, defs

    # Parse target functions from the given files
    def parse(self, cncrt_name, summ_name):
        cncrt_name, summ_name, entries, defs = self.definitions(
            cncrt_name, summ_name
        )
        def_nodes = [d.definition if d is not None else None for d in defs]
        args = self.arguments(entries)
        ret = self.returnType(entries)

        return cncrt_name, summ_name, def_nodes, args, ret
