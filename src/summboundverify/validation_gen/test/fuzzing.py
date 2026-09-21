from typing import Any

from pycparser.c_ast import (
    Decl,
    Node,
    FuncDef,
)

from ..api import (
    sbv_record,
    get_cnstr,
    store_cnstr,
    halt_all,
)

from .base import TestGen
from ..utils import return_value


class SummaryFuzzTestGen(TestGen):
    """
    Generates tests that execute the summary symbolically.

    The resulting constraints are recorded for the fuzzing phase.
    """

    def __init__(
        self,
        args: list[Node] | None,
        ret: Decl,
        summary_name: str,
        memory: bool,
        max_args: list[Any] | None,
    ) -> None:
        super().__init__(args, ret, memory, max_args)

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

        if self.memory:
            body.extend(
                self._tag_memory(sym_args.pointer_args, size_macro)
            )

        body.extend(self._summary_body(call_args, test_id))
        body.append(return_value(None))

        return self._function(name, body)

    def _summary_body(self, call_args: list[str], test_id: int) -> list[Node]:
        return [
            self._call_function(
                self.summary_name,
                call_args,
                "ret",
            ),
            get_cnstr("cnstr", "ret", self.ret),
            store_cnstr(
                f"summ_test{test_id}",
                "cnstr",
            ),
            halt_all("NULL"),
        ]


class ConcreteFuzzTestGen(TestGen):
    """
    Generates tests that execute the concrete function natively.

    The returned value is recorded for the fuzzing phase.
    """

    def __init__(
        self,
        args: list[Node] | None,
        ret: Decl,
        concrete_name: str,
        memory: bool,
        max_args: list[Any] | None,
    ) -> None:
        super().__init__(args, ret, memory, max_args)

        self.concrete_name = concrete_name

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
                "ret",
            ),
            sbv_record(
                f"test_{test_id}",
                "ret",
                self.ret,
                self._returns_void(self.ret),
                self._returns_pointer(self.ret),
            ),
        ]
