from typing import Any
from abc import ABC, abstractmethod

from pycparser.c_ast import (
    ID,
    Decl,
    Node,
    FuncDef,
    Compound,
    ExprList,
    FuncCall,
    FuncDecl,
    PtrDecl,
    TypeDecl,
    IdentifierType,
)

from .args import SymbolicArgGen

from ..api import mem_addr


class TestGen(ABC):
    """Common functionality for generating validation tests."""

    def __init__(
        self,
        args: list[Node] | None,
        ret: Decl,
        memory: bool,
        max_args: list[Any] | None,
    ) -> None:
        self.args = args
        self.ret = ret
        self.memory = memory
        self.max_args = max_args or []

    @staticmethod
    def _returns_void(node: Node) -> bool:
        return isinstance(node, TypeDecl) and node.type.names == ["void"]

    @staticmethod
    def _returns_pointer(node: Node) -> bool:
        return isinstance(node, PtrDecl)

    def _call_function(
        self,
        name: str,
        call_args: list[str],
        ret_name: str,
    ) -> Node:

        call = FuncCall(
            ID(name),
            ExprList([ID(arg) for arg in call_args]),
        )

        if self._returns_void(self.ret):
            return call

        lvalue = TypeDecl(ret_name, [], None, self.ret)

        return Decl(
            ret_name,
            [], [], [], [],
            lvalue,
            call,
            None,
        )

    @staticmethod
    def _tag_memory(ptr_names: list[str], size_macro: str | list[str] | None) -> list[Node]:

        if isinstance(size_macro, list):
            return [
                mem_addr(ptr, size)
                for ptr, size in zip(ptr_names, size_macro)
            ]

        return [mem_addr(ptr, size_macro) for ptr in ptr_names]

    def _create_args(
        self,
        size_macro: str | list[str] | None,
        null_bytes: list[Any] | None,
        max_macro: Any,
        default: dict[int, Any] | None,
        concrete: dict[int, Any] | None,

    ) -> tuple[list[Node], list[str], SymbolicArgGen]:

        sym_args = SymbolicArgGen(
            self.args,
            size_macro,
            null_bytes,
            max_macro,
            self.max_args
        )

        args_code = sym_args.create_symbolic_args(default, concrete)

        return args_code, sym_args.call_args, sym_args

    @staticmethod
    def _function(name: str, body: list[Node]) -> FuncDef:
        decl = Decl(
            name,
            [], [], [], [],
            FuncDecl(
                None,
                TypeDecl(
                    name, [], None,
                    IdentifierType(names=["void"]),
                ),
            ),
            None, None
        )

        return FuncDef(decl, None, Compound(body))

    @abstractmethod
    def create_test(
        self,
        name: str,
        size_macro: str | list[str] | None,
        null_bytes: list[Any] | None,
        max_macro: Any,
        default: dict[int, Any] | None,
        concrete: dict[int, Any] | None,
        test_id: int,
    ) -> FuncDef:
        pass
