from typing import Any

from pycparser.c_ast import (
    Decl,
    Node,
    FuncDef,
)

from ..api import (
    save_current_state,
    get_cnstr,
    store_cnstr,
    halt_all,
    check_implications,
    print_counterexamples,
)

from ..utils import return_value

from .base import TestGen


class SymbolicTestGen(TestGen):
    """
    Generates symbolic differential tests.

    The concrete function and its summary are executed in the same
    symbolic run and their results are checked for mutual implication.
    """

    def __init__(
        self,
        args: list[Node] | None,
        ret: Decl,
        concrete_name: str,
        summary_name: str,
        memory: bool,
        max_args: list[Any] | None,
    ):
        super().__init__(args, ret, memory, max_args)
        self.concrete_name = concrete_name
        self.summary_name = summary_name

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

        args_code, call_args, sym_args = self._create_args(
            size_macro,
            null_bytes,
            max_macro,
            default,
            concrete,
        )

        body: list[Node] = [*args_code]
        body.append(save_current_state("initial_state"))

        if self.memory:
            body.extend(
                self._tag_memory(sym_args.pointer_args, size_macro)
            )

        body.extend(self._body(call_args, test_id))
        body.append(return_value(None))

        return self._function(name, body)

    def _body(self, call_args: list[str], test_id: int) -> list[Node]:

        return [
            self._call_function(
                self.concrete_name,
                call_args,
                "ret1",
            ),
            get_cnstr("cnstr1", "ret1", self.ret),
            store_cnstr(
                f"cnctr_test{test_id}",
                "cnstr1",
            ),

            halt_all("initial_state"),

            self._call_function(
                self.summary_name,
                call_args,
                "ret2",
            ),
            get_cnstr("cnstr2", "ret2", self.ret),
            store_cnstr(
                f"summ_test{test_id}",
                "cnstr2",
            ),

            halt_all("NULL"),

            check_implications(
                "result",
                f"cnctr_test{test_id}",
                f"summ_test{test_id}",
            ),

            print_counterexamples("result"),
        ]
