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
* File I/O and floating point were in here too, on the theory that angr cannot
  model them. The real limit is earlier and cheaper to see: the *test
  generator* cannot build arguments of those types (`double x =
  sym_var_named(...)` does not compile, nor does `sizeof(FILE)`), so those
  targets fail to build for **both** engines. Skipping symbolic execution
  there would hand the work to a fuzzing run that is equally doomed.

What is left is the case where the test builds and runs fine, but symbolic
execution specifically cannot finish it.
"""

import logging

from pathlib import Path

from pycparser.c_ast import FuncDef, NodeVisitor

from summboundverify.exceptions import MissingFunctionError
from summboundverify.utils.summary import FunctionType

from summboundverify.validation_gen.utils import parse_c_file
from summboundverify.validation_gen.function_parser.visitors import FunctionVisitor

logger = logging.getLogger(__name__)


# Calls that end the process or leave the frame without returning. angr has
# nowhere to continue from, so the path simply disappears.
NONLOCAL_FLOW = frozenset({
    'exit', '_exit', 'abort', 'longjmp', 'setjmp',
    'fork', 'pthread_create', 'pthread_join',
})


class _Calls(NodeVisitor):
    """Collect the function calls made inside a definition."""

    def __init__(self):
        self.calls: set[str] = set()

    def visit_FuncCall(self, node):
        name = getattr(node.name, 'name', None)
        if isinstance(name, str):
            self.calls.add(name)
        self.generic_visit(node)


def se_obstacles(definition: FuncDef) -> list[str]:
    """Reasons symbolic execution cannot finish this function.

    Empty when there are none, so the result doubles as a predicate.
    """
    visitor = _Calls()
    visitor.visit(definition)

    calls = visitor.calls
    obstacles = []

    # Verified: a recursive concrete function runs until the timeout rather
    # than returning a verdict, because the generated test bounds its inputs
    # but nothing bounds the recursion depth symbolically.
    if definition.decl.name in calls:
        obstacles.append("is recursive")

    if hits := calls & NONLOCAL_FLOW:
        names = ", ".join(sorted(hits))
        obstacles.append(f"leaves through non-local control flow ({names})")

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
        definition = list(functions.values())[-1]
    elif fname in functions:
        definition = functions[fname]
    else:
        raise MissingFunctionError(FunctionType.concrete, file, fname)

    return se_obstacles(definition)
