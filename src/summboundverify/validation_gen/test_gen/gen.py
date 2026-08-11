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

from ..api_gen.gen import *
from ..utils import return_value
from .arg_gen import SymbolicArgs


class TestGen:
    """Generates validation tests for a concrete function and its summary.

    Three shapes come out of here, one per consumer:

    * `se` exercises both functions in the same symbolic run and asks angr to
      prove the implications between them. It is the only one that grades.
    * `summary` runs the summary alone, symbolically, and stores one formula
      per path -- the `(pc, sr)` the sampling check needs.
    * `concrete` runs the concrete function alone, natively, and writes down
      what it returned for the inputs it was handed.

    The last two are the two halves of a fuzzing run, and they share the whole
    argument-construction path: the same declarations, the same names, the
    same bounds. That is not a convenience, it is the correctness condition --
    a sample can only be checked against a formula if both sides agree on what
    each input variable is called.
    """

    def __init__(
        self,
        args: list[Node] | None,
        ret: Decl,
        cncrt_name: str,
        summ_name: str,
        memory: bool,
        max_args: list[Any] | None,
        mode: str = 'se',
    ) -> None:
        self.args = args
        self.ret = ret
        self.cncrt_name = cncrt_name
        self.summ_name = summ_name
        self.memory = memory
        self.max_args = max_args or []
        self.mode = mode

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

    def _differential_body(self, call_args, test_id) -> list[Node]:
        """Both functions, symbolically, compared by check_implications."""
        return [
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
        ]

    def _summary_body(self, call_args, test_id) -> list[Node]:
        """The summary alone, symbolically.

        No `save_current_state`: nothing is resumed here, because there is no
        second call to line up against. Each path that reaches `halt_all(NULL)`
        has already stored its own formula, so what survives the run is the
        list of `(pc, sr)` pairs the sampling check consumes.
        """
        return [
            self.call_function(self.summ_name, call_args, "ret", self.ret),
            get_cnstr("cnstr", "ret", self.ret),
            store_cnstr(f"summ_test{test_id}", "cnstr"),

            halt_all("NULL"),
        ]

    def _concrete_body(self, call_args, test_id) -> list[Node]:
        """The concrete function alone, natively, recording what it produced.

        `sbv_record` sits exactly where `get_cnstr` sits in the symbolic
        bodies, and reads exactly the same things -- the return value and the
        memory tagged by `mem_addr`. Keeping the two in step is what makes a
        sample comparable to a formula.
        """
        return [
            self.call_function(self.cncrt_name, call_args, "ret", self.ret),
            sbv_record(
                f"test_{test_id}", "ret", self.ret,
                self._returns_void(self.ret),
            ),
        ]

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
        sym_args = SymbolicArgs(
            self.args, size_macro, null_bytes, max_macro, self.max_args
        )

        args_code = sym_args.create_symbolic_args(default, concrete)
        call_args = sym_args.call_args

        body: list[Node] = [*args_code]

        # Only the differential body resumes anything, and it has to snapshot
        # before the memory tags to keep the emitted test byte-identical to
        # what it was before the sampling modes existed.
        if self.mode == 'se':
            body.append(save_current_state("initial_state"))

        if self.memory:
            body.extend(self.tag_memory(sym_args.pointer_args, size_macro))

        if self.mode == 'summary':
            body.extend(self._summary_body(call_args, test_id))
        elif self.mode == 'concrete':
            body.extend(self._concrete_body(call_args, test_id))
        else:
            body.extend(self._differential_body(call_args, test_id))

        body.append(return_value(None))

        block = Compound(body)

        decl = Decl(
            name, [], [], [], [],
            FuncDecl(None, TypeDecl(name, [], None,
                     IdentifierType(names=["void"]))),
            None, None,
        )

        return FuncDef(decl, None, block)
