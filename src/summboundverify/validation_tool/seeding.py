"""Seeding the fuzzing campaign from the summary's own formula.

AFL++ keeps an input when it reaches new coverage *of the concrete function*.
That is the wrong yardstick for this job, and measurably so: on tolower, a
campaign of 40 000 executions discovered two inputs beyond the seeds, because
the function has one branch and there is nothing else to find. Meanwhile a
summary whose fold range was narrowed by one went undetected -- 'Z' and 'F'
take the same branch of the concrete function, so the fuzzer has no reason to
keep both, and only one of them contradicts the summary.

The boundaries that matter are the *summary's*. They are already known before
the campaign starts, sitting in the path conditions the symbolic run produced,
so this reads them off and turns them into seed inputs:

* one model per path, so every branch of the summary is exercised at least
  once;
* for every comparison against a constant, that constant and its immediate
  neighbours, which is where an off-by-one lives.

AFL++ then mutates around inputs that are already interesting, instead of
starting from tapes chosen for a different purpose.

Turning a chosen assignment back into a tape needs the harness's draw layout.
That is not re-derived here: the harness reports the offset and length of
every draw when it records, so the layout comes from a single probe run of the
real thing.
"""

import logging

from z3 import (
    BitVecNumRef,
    BitVecRef,
    BoolRef,
    Solver,
    is_app,
    is_bv,
    is_bv_value,
    sat,
)
from z3.z3util import get_vars

logger = logging.getLogger(__name__)

# Ceiling on generated seeds. Every one costs a file and an execution; past a
# point the fuzzer's own mutation is a better use of the budget.
MAX_SEEDS = 64

# How far around a constant to look. An off-by-one is the overwhelmingly
# common boundary error, and each extra step multiplies the seed count.
NEIGHBOURHOOD = (-1, 0, 1)


def _numerals(expr) -> set[int]:
    """Every bitvector constant appearing anywhere in a formula."""
    found: set[int] = set()
    stack = [expr]
    seen = set()

    while stack:
        node = stack.pop()

        key = node.get_id()
        if key in seen:
            continue
        seen.add(key)

        if is_bv_value(node):
            found.add(node.as_long())
            continue

        if is_app(node):
            stack.extend(node.children())

    return found


def candidates(formula: BoolRef) -> dict[str, list[int]]:
    """Values worth trying for each input variable.

    Every constant the formula mentions, plus its neighbours. Which constant
    belongs to which variable is not worked out here: the formula is small,
    the extra candidates are cheap, and a candidate that makes no sense for a
    variable simply produces a model that is no worse than a random one.
    """
    variables = [v for v in get_vars(formula) if is_bv(v)]
    constants = _numerals(formula)

    values: dict[str, list[int]] = {}

    for var in variables:
        name = var.decl().name()

        # `Ret` is an output; pinning it would be asking the fuzzer to produce
        # a result rather than to try an input.
        if name == 'Ret' or name.startswith('mem_'):
            continue

        limit = (1 << var.size()) - 1
        wanted = []

        for constant in sorted(constants):
            for step in NEIGHBOURHOOD:
                candidate = constant + step
                if 0 <= candidate <= limit and candidate not in wanted:
                    wanted.append(candidate)

        values[name] = wanted

    return values


def assignments(formula: BoolRef, limit: int = MAX_SEEDS) -> list[dict]:
    """Input assignments worth sampling, as {variable name: value}.

    Each one is a full model, so the variables a candidate says nothing about
    still get values the summary considers possible. An assignment that cannot
    be satisfied is dropped rather than forced: an input outside every path
    condition tells the campaign nothing the bounds do not already say.
    """
    out: list[dict] = []
    seen: set[tuple] = set()

    def record(model) -> None:
        assignment = {
            d.name(): model[d].as_long()
            for d in model.decls()
            if isinstance(model[d], BitVecNumRef)
            and d.name() != 'Ret'
            and not d.name().startswith('mem_')
        }

        if not assignment:
            return

        key = tuple(sorted(assignment.items()))
        if key in seen:
            return

        seen.add(key)
        out.append(assignment)

    solver = Solver()
    solver.add(formula)

    # One model of the summary as a whole: somewhere it admits.
    if solver.check() == sat:
        record(solver.model())

    for name, values in candidates(formula).items():
        var = next(
            (v for v in get_vars(formula) if v.decl().name() == name), None
        )

        if var is None or not isinstance(var, BitVecRef):
            continue

        for value in values:
            if len(out) >= limit:
                logger.debug("Seed ceiling of %d reached", limit)
                return out

            solver.push()
            solver.add(var == value)

            if solver.check() == sat:
                record(solver.model())

            solver.pop()

    return out


def tape_layout(sample) -> list[tuple[str, int, int]]:
    """Where each drawn input lives on the tape: (name, offset, length).

    Read off a recorded sample rather than reconstructed from the generated
    source, so it is the layout the harness actually uses -- including the
    cases where a draw takes fewer bytes than its width suggests.
    """
    return [
        (name, value.offset, value.length)
        for name, value in sample.inputs.items()
        if value.length
    ]


def build_tape(layout: list, assignment: dict, size: int) -> bytes:
    """A tape that makes the harness draw `assignment`.

    Variables the assignment says nothing about keep their zero bytes, which
    the harness reads as zero rather than as a short tape.
    """
    tape = bytearray(size)

    for name, offset, length in layout:
        if name not in assignment:
            continue

        if offset + length > size:
            continue

        value = assignment[name] & ((1 << (length * 8)) - 1)
        tape[offset:offset + length] = value.to_bytes(length, 'little')

    return bytes(tape)


def seed_tapes(formulas: list, sample, size: int,
               limit: int = MAX_SEEDS) -> list[bytes]:
    """Tapes covering the summary's paths and the boundaries in them.

    Empty when there is nothing to work from -- no formula, or a probe that
    drew nothing -- in which case the caller keeps its generic corpus.
    """
    from .sample_check import summary_formula

    formula = summary_formula(formulas or [])
    if formula is None:
        return []

    layout = tape_layout(sample)
    if not layout:
        return []

    tapes = []
    seen = set()

    for assignment in assignments(formula, limit):
        tape = build_tape(layout, assignment, size)

        if tape in seen:
            continue

        seen.add(tape)
        tapes.append(tape)

    return tapes
