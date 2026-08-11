from pathlib import Path
from dataclasses import dataclass, field

from pycparser.c_ast import Node, ParamList
from pycparser.c_generator import CGenerator

from summboundverify.exceptions import (
    ArgumentMismatchError,
    MissingFunctionError,
    ReturnMismatchError,
)

from summboundverify.utils.summary import FunctionType

from .visitors import FunctionVisitor, Function
from ..test_gen.arg_gen import SymbolicArgs
from ..utils import parse_file

_CGEN = CGenerator()


@dataclass
class ParsedFunctions:
    concrete_name: str
    summary_name: str
    functions: list[Function | None]
    arguments: ParamList
    return_type: Node

    concrete_functions: list[Function | None] = field(default_factory=list)
    summary_functions: list[Function | None] = field(default_factory=list)


class FunctionParser:

    def __init__(
        self,
        concrete: str | Path | None,
        summary: str | Path | None
    ):
        self.concrete = Path(concrete) if concrete else None
        self.summary = Path(summary) if summary else None

        self.cnctr_functions = (
            self._load_functions(self.concrete)
            if self.concrete else None
        )

        self.summ_functions = (
            self._load_functions(self.summary)
            if self.summary else None
        )

    def _load_functions(self, file: Path) -> dict[str, Function]:
        ast = parse_file(str(file))
        return FunctionVisitor(ast, file).functions()

    def _get_function(
        self,
        functions: dict[str, Function],
        name: str | None,
        file: Path,
        ftype: FunctionType,
    ) -> tuple[str, Function, list[Function]]:

        if not functions:
            raise MissingFunctionError(ftype, file)

        if name is None:
            name, function = next(reversed(functions.items()))
        else:
            try:
                function = functions[name]
            except KeyError:
                raise MissingFunctionError(ftype, file, name)

        return name, function, list(functions.values())

    def _args(self, function: Function) -> list[str]:
        visitor = SymbolicArgs(function.args)
        return visitor.types

    def arguments(self, concrete: Function | None, summary: Function | None) -> ParamList:

        concrete_args = []
        summary_args = []
        args_def = None

        if concrete:
            concrete_args = self._args(concrete)
            args_def = concrete.args

        if summary:
            summary_args = self._args(summary)
            args_def = summary.args

        if (
            concrete_args
            and summary_args
            and concrete_args != summary_args
        ):
            raise ArgumentMismatchError(
                concrete_args,
                summary_args,
            )

        assert args_def is not None
        return args_def

    def return_type(self, concrete: Function | None, summary: Function | None) -> Node:

        concrete_ret = None
        summary_ret = None
        ret_def = None

        if concrete:
            concrete_ret = concrete.return_type
            ret_def = concrete_ret

        if summary:
            summary_ret = summary.return_type
            ret_def = summary_ret

        if (
            concrete_ret and summary_ret and
            _CGEN.visit(concrete_ret) != _CGEN.visit(summary_ret)
        ):
            raise ReturnMismatchError(
                _CGEN.visit(concrete_ret),
                _CGEN.visit(summary_ret),
            )

        assert ret_def is not None
        return ret_def

    def parse(self, concrete: str | None, summary: str | None) -> ParsedFunctions:

        concrete_functions = [None]
        summary_functions = [None]

        concrete_entry = None
        summary_entry = None

        concrete_name = None
        summary_name = None

        if self.cnctr_functions:
            (
                concrete_name,
                concrete_entry,
                concrete_functions,

            ) = self._get_function(
                self.cnctr_functions,
                concrete,
                self.concrete,      # type: ignore
                FunctionType.concrete,
            )
        else:
            assert concrete is not None
            concrete_name = concrete

        if self.summ_functions:
            (
                summary_name,
                summary_entry,
                summary_functions,

            ) = self._get_function(
                self.summ_functions,
                summary,
                self.summary,       # type: ignore
                FunctionType.summary,
            )
        else:
            assert summary is not None
            summary_name = summary

        arguments = self.arguments(concrete_entry, summary_entry)
        return_type = self.return_type(concrete_entry, summary_entry)

        parsed = ParsedFunctions(
            concrete_name=concrete_name,
            summary_name=summary_name,
            functions=[
                *concrete_functions,
                *summary_functions,
            ],
            arguments=arguments,
            return_type=return_type,
            concrete_functions=list(concrete_functions),
            summary_functions=list(summary_functions),
        )

        return parsed
