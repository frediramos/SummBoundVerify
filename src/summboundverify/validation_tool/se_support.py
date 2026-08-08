"""Whether symbolic execution can say anything useful about a target.

angr *executes* the generated test, so a concrete function it cannot follow
does not yield a weaker verdict -- it yields none at all, usually by running
until the timeout. This refuses those targets up front and names the reason,
overriding an explicit `--engine se`, because fuzzing can still validate them
and a run that hangs for the full timeout helps nobody.

The criterion is deliberately narrow, and it is narrow because measuring it
showed a wide one to be wrong:

* `malloc` and friends were in here at first. They should not be: angr models
  allocation perfectly well, and `tests/libc/synth/*/strdup` passes under
  symbolic execution while calling `malloc`.
* File I/O was in here too, on the theory that angr cannot model it. The real
  limit is earlier and cheaper to see: the *test generator* cannot build a
  `FILE *` argument (`sizeof(FILE)` does not compile), so those targets fail
  to build for **both** engines. Skipping symbolic execution there would hand
  the work to a fuzzing run that is equally doomed, so it is not listed until
  the generator can build them.

What is left is what the generator *can* build and fuzzing *can* run, but
symbolic execution cannot: either it never finishes, or the primitive the
argument needs has no symbolic counterpart at this word size.
"""

import logging

from pathlib import Path

from pycparser.c_ast import NodeVisitor

from summboundverify.exceptions import MissingFunctionError
from summboundverify.utils.summary import FunctionType

from summboundverify.validation_gen.utils import parse_c_file
from summboundverify.validation_gen.function_parser.visitors import (
    Function,
    FunctionVisitor,
)

logger = logging.getLogger(__name__)


# Calls that end the process or leave the frame without returning. angr has
# nowhere to continue from, so the path simply disappears.
NONLOCAL_FLOW = frozenset({
    'exit', '_exit', 'abort', 'longjmp', 'setjmp',
    'fork', 'pthread_create', 'pthread_join',
})

# Argument types drawn through sym_var_bytes(). The concrete runtime fills
# them byte by byte, which works at any width; the symbolic backend has to
# mint a bitvector no wider than the architecture, so a double is refused
# outright at -m32. Fuzz-only, therefore.
FLOAT_TYPES = frozenset({'float', 'double', 'long double'})


class _Calls(NodeVisitor):
    """Collect the function calls made inside a body."""

    def __init__(self):
        self.calls: set[str] = set()

    def visit_FuncCall(self, node):
        name = getattr(node.name, 'name', None)
        if isinstance(name, str):
            self.calls.add(name)
        self.generic_visit(node)


class _Types(NodeVisitor):
    """Collect the base types named in a declaration."""

    def __init__(self):
        self.types: set[str] = set()

    def visit_IdentifierType(self, node):
        self.types.add(" ".join(node.names))


def se_obstacles(function: Function) -> list[str]:
    """Reasons symbolic execution cannot handle this function.

    Empty when there are none, so the result doubles as a predicate.

    Calls come from the body and types from the declaration, so a function
    that merely *returns* a double is caught as readily as one that takes it.
    A function with no body (a bare prototype) contributes no calls.
    """
    calls_visitor = _Calls()
    calls_visitor.visit(function.body) if function.body is not None else None

    types_visitor = _Types()
    types_visitor.visit(function.declaration)

    calls = calls_visitor.calls
    obstacles = []

    # Verified: a recursive concrete function runs until the timeout rather
    # than returning a verdict, because the generated test bounds its inputs
    # but nothing bounds the recursion depth symbolically.
    if function.name in calls:
        obstacles.append("is recursive")

    if hits := calls & NONLOCAL_FLOW:
        names = ", ".join(sorted(hits))
        obstacles.append(f"leaves through non-local control flow ({names})")

    if hits := types_visitor.types & FLOAT_TYPES:
        names = ", ".join(sorted(hits))
        obstacles.append(f"takes or returns floating point ({names})")

    return obstacles


def se_obstacles_in(file: str | Path, fname: str | None = None) -> list[str]:
    """`se_obstacles` for the target function of a source file.

    With no name, the last definition in the file is taken, the same choice
    `FunctionParser.get_def` makes, so both look at the same function.
    """
    file = Path(file)
    functions = FunctionVisitor(parse_c_file(file), file).functions()

    if not functions:
        raise MissingFunctionError(FunctionType.concrete, file)

    if fname is None:
        _, function = next(reversed(functions.items()))
    elif fname in functions:
        function = functions[fname]
    else:
        raise MissingFunctionError(FunctionType.concrete, file, fname)

    return se_obstacles(function)
