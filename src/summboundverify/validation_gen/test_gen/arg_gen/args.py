from itertools import repeat
from typing import Any, Iterator

from pycparser.c_ast import Node

from .visitors.function_args import ArgVisitor


class SymbolicArgs:
    """Generates the symbolic variables required to call a function.

    The class visits each function argument using ``ArgVisitor`` and collects:

    - the declarations needed to construct symbolic arguments;
    - the argument expressions for the function call;
    - the inferred argument types;
    - the mapping between argument names and their types.

    Parameters
    ----------
    args:
        Function arguments from the parsed C AST.
    size_macro:
        Optional size (or list of sizes) used when creating symbolic arrays.
        If a list is provided, one value is consumed per argument.
    null_bytes:
        Optional null-termination specification (or list of specifications).
        If a list is provided, one value is consumed per argument.
    max_macro:
        Optional macro defining the maximum symbolic size.
    max_args:
        Additional arguments passed directly to ``ArgVisitor``.
    """

    def __init__(
        self,
        args: list[Node] | None,
        size_macro: Any = None,
        null_bytes: list[Any] | None = None,
        max_macro: Any = None,
        max_args: list[Any] | None = None,
    ) -> None:
        self._args = args or []

        self._max_macro = max_macro
        self._max_args = max_args or []

        self._size_values = self._iterator(size_macro)
        self._null_values = self._iterator(null_bytes)

        self._code: list[Any] = []
        self._call_args: list[str] = []
        self._types: list[Any] = []
        self._arg_types: dict[str, Any] = {}

    @staticmethod
    def _iterator(values: Any) -> Iterator[Any]:
        """Return an iterator over ``values``.

        Lists are consumed one element at a time.
        Any other value is repeated indefinitely.
        """
        if isinstance(values, list):
            return iter(values)

        return repeat(values)

    def create_symbolic_args(
        self,
        default: dict[int, Any] | None = None,
        concrete: dict[int, Any] | None = None,
    ) -> list[Any]:
        """Generate the symbolic arguments.

        Parameters
        ----------
        default:
            Maps a 1-based argument index to its default value.
        concrete:
            Maps a 1-based argument index to a concrete value.

        Returns
        -------
        list
            The generated declarations required before invoking the function.
        """
        default = default or {}
        concrete = concrete or {}

        for index, arg in enumerate(self._args, start=1):
            default_value = default.get(index)

            visitor = ArgVisitor(
                next(self._size_values, None),
                self._max_macro,
                next(self._null_values, None),
                self._max_args,
                default_value,
                concrete.get(index),
            )

            visitor.visit(arg)

            argument = visitor.argname
            assert argument is not None

            if default_value == "&":
                argument = f"&{argument}"

            arg_type = visitor.get_type()

            self._call_args.append(argument)
            self._code.extend(visitor.gen_code())
            self._types.extend(arg_type)
            self._arg_types[argument] = arg_type

        return self._code

    @property
    def types(self) -> list[Any]:
        """Return the inferred argument types."""
        if not self._types:
            self.create_symbolic_args()

        return self._types

    @property
    def call_args(self) -> list[str]:
        """Return the generated function call arguments."""
        return self._call_args

    @property
    def pointer_args(self) -> list[str]:
        """Return the names of pointer arguments."""
        return [
            name
            for name, arg_type in self._arg_types.items()
            if arg_type[1]
        ]
