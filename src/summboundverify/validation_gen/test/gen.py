from typing import Any

from pycparser.c_ast import (
    ID,
    Decl,
    Node,
    FuncDef,
    Compound,
    ExprList,
    FuncCall,
    FuncDecl,
    TypeDecl,
    IdentifierType,
)
from .args import SymbolicArgGen

from ..api import (
    mem_addr,
    save_current_state,
    get_cnstr,
    store_cnstr,
    halt_all,
    check_implications,
    print_counterexamples
)

from ..utils import return_value


class TestGen:
    """Generates validation tests for a concrete function and its summary."""

    def __init__(
        self,
        args: list[Node] | None,
        ret: Decl,
        cncrt_name: str,
        summ_name: str,
        memory: bool,
        max_args: list[Any] | None,
    ) -> None:
        self.args = args
        self.ret = ret
        self.cncrt_name = cncrt_name
        self.summ_name = summ_name
        self.memory = memory
        self.max_args = max_args or []

    def _returns_void(self, node):
        return isinstance(node, TypeDecl) and node.type.names == ["void"]

    def call_function(
        self,
        name: str,
        call_args: list[str],
        ret_name: str,
        ret_type: Decl,
    ) -> Node:
        """Generate a function call, assigning its result if non-void."""

        call = FuncCall(ID(name), ExprList([ID(arg) for arg in call_args]))

        if self._returns_void(ret_type):
            return call

        lvalue = TypeDecl(ret_name, [], None, ret_type)
        return Decl(ret_name, [], [], [], [], lvalue, call, None)

    def tag_memory(
        self,
        ptr_names: list[str],
        size_macro: str | list[str] | None,
    ) -> list[Node]:
        """Generate memory tags for pointer arguments."""

        if isinstance(size_macro, list):
            return [mem_addr(ptr, size) for ptr, size in zip(ptr_names, size_macro)]

        return [mem_addr(ptr, size_macro) for ptr in ptr_names]

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
        """Generate a validation test."""
        sym_args = SymbolicArgGen(
            self.args, size_macro, null_bytes, max_macro, self.max_args
        )

        args_code = sym_args.create_symbolic_args(default, concrete)
        call_args = sym_args.call_args

        body: list[Node] = [*args_code, save_current_state("initial_state")]

        if self.memory:
            body.extend(self.tag_memory(sym_args.pointer_args, size_macro))

        body.extend([
            self.call_function(self.cncrt_name, call_args, "ret1", self.ret),
            get_cnstr("cnstr1", "ret1", self.ret),
            store_cnstr(f"cnctr_test{test_id}", "cnstr1"),

            halt_all("initial_state"),

            self.call_function(self.summ_name, call_args, "ret2", self.ret),
            get_cnstr("cnstr2", "ret2", self.ret),
            store_cnstr(f"summ_test{test_id}", "cnstr2"),

            halt_all("NULL"),

            check_implications(
                "result",
                f"cnctr_test{test_id}",
                f"summ_test{test_id}",
            ),

            print_counterexamples("result"),
            return_value(None),
        ])

        block = Compound(body)

        decl = Decl(
            name, [], [], [], [],
            FuncDecl(None, TypeDecl(name, [], None,
                     IdentifierType(names=["void"]))),
            None, None,
        )

        return FuncDef(decl, None, block)
