"""Whether symbolic execution can say anything useful about a target.

Symbolic execution runs *both* the summary and the concrete function, and the
concrete function is the hard one: it is ordinary C with loops, allocation and
recursion, and when angr cannot follow it the result is not a weaker verdict
but none at all, usually by running until the timeout. This refuses those
targets up front and names the reason, overriding an explicit `--engine se`.

Sampling has no such problem, and that asymmetry is the whole reason this
module exists. It never executes the concrete function symbolically -- it runs
it natively under AFL++ and only reasons about the summary, which is written
against the API and is loop-free by construction. So a target refused here is
not a target that cannot be validated; it is one that goes to the other
engine.

The criterion is deliberately narrow, and it is narrow because measuring it
showed a wide one to be wrong. Four rules have been added on plausible
reasoning and removed on evidence:

* `malloc` and friends. angr models allocation perfectly well, and the strdup
  tests pass under symbolic execution while calling it.
* File I/O, on the theory that angr cannot model it. The real limit was
  earlier: the generator cannot build a `FILE *` at all, so those targets fail
  for **both** engines and skipping symbolic execution only hands the work to
  a run that is equally doomed.
* Non-local control flow (`exit`, `abort`, `longjmp`), on the reasoning that
  the symbolic path disappears. A concrete function calling `exit(1)`
  terminates the harness, which AFL++ records as a crash -- so handing the
  target to sampling was *worse* than not skipping, because it manufactured a
  finding. Fixed at the source instead, with `sbv_exit`.
* Floating point, because `sym_var` refused a bitvector wider than the
  architecture. That was a restriction on the wrong primitive: `sym_var_bytes`
  writes through a pointer and never returns the value in a register, so a
  64-bit double is fine at -m32. Lifted.

The rule that survives all of this: only skip symbolic execution when sampling
can genuinely take over. Anything else trades a missing verdict for a false
one.
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
