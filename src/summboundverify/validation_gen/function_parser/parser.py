from pathlib import Path
from dataclasses import dataclass, field

from pycparser.c_ast import (
    IdentifierType,
    Node,
    NodeVisitor,
    ParamList,
    TypeDecl,
)
from pycparser.c_generator import CGenerator

from summboundverify.exceptions import (
    ArgumentMismatchError,
    MissingFunctionError,
    ReturnMismatchError,
)

from summboundverify.utils.summary import FunctionType
from summboundverify.utils.unsupported import check_supported

from .visitors import FunctionVisitor, Function
from ..test_gen.arg_gen import SymbolicArgs
from ..utils import parse_file

_CGEN = CGenerator()


class _BaseType(NodeVisitor):
    """The base type a declaration names, and whether it sits behind a
    pointer.

    An array counts as a pointer: the generated test draws its elements one
    by one, so what matters is that the declaration does not *hold* the value
    itself.
    """

    def __init__(self):
        self.name: str | None = None
        self.pointer: bool = False

    def visit_PtrDecl(self, node):
        self.pointer = True
        self.visit(node.type)

    def visit_ArrayDecl(self, node):
        self.pointer = True
        self.visit(node.type)

    def visit_IdentifierType(self, node):
        self.name = " ".join(node.names)


class _Typedefs(NodeVisitor):
    """Every typedef in the parsed sources, as name -> (base type, pointer).

    Collected across both files, because a summary and its concrete function
    are free to spell the same alias in either of them.
    """

    def __init__(self):
        self.aliases: dict[str, tuple[str, bool]] = {}

    def visit_Typedef(self, node):
        base = _BaseType()
        base.visit(node.type)

        if base.name is not None:
            self.aliases[node.name] = (base.name, base.pointer)


def _resolve(name: str, aliases: dict[str, tuple[str, bool]]) -> tuple[str, bool]:
    """Follow a typedef chain down to the type it really names.

    `typedef double real_t` has to be refused exactly as a bare `double` is,
    or the guard is worth nothing to anyone who names their types. The `seen`
    set is there because a chain in a hand-written header can be circular.
    """
    pointer = False
    seen: set[str] = set()

    while name in aliases and name not in seen:
        seen.add(name)
        name, ptr = aliases[name]
        pointer = pointer or ptr

    return name, pointer


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

        # Filled by _load_functions, from whichever files are present.
        self._typedefs = _Typedefs()

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
        self._typedefs.visit(ast)
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
        self._check_arg_types(args_def)
        return args_def

    def _check_arg_types(self, args: ParamList) -> None:
        """Refuse an argument the generator cannot draw a value for.

        A pointer is refused alongside a plain value here, unlike in the
        return type: the test fills what it points at, element by element,
        so `double *` is as undrawable as `double`.
        """
        for param in getattr(args, 'params', None) or []:
            base = _BaseType()
            base.visit(param)

            if base.name is None:
                continue

            typename, _ = _resolve(base.name, self._typedefs.aliases)
            where = f"argument '{param.name}'" if param.name else "an argument"
            check_supported(typename, where)

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

        # Only a value returned directly: a `double *` hands back an address,
        # which travels through a `symbolic` intact.
        if isinstance(ret_def, TypeDecl)                 and isinstance(ret_def.type, IdentifierType):
            typename, pointer = _resolve(
                " ".join(ret_def.type.names), self._typedefs.aliases
            )
            if not pointer:
                check_supported(typename, "return type")

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
