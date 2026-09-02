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

Reaching a branch is not the same as seeing what it did, though, and a model
chosen for the branch alone routinely cannot tell. A summary copying `len-1`
bytes instead of `len` is refuted only by an input whose last byte differs
between source and destination: on the all-zero buffers a solver hands back
when nothing pins them, the byte it failed to copy and the byte it copied
correctly are both zero, and the sample matches. So the assignment is
additionally asked to make the output *observable* -- see `observability`.

AFL++ then mutates around inputs that are already interesting, instead of
starting from tapes chosen for a different purpose.

Turning a chosen assignment back into a tape needs the harness's draw layout.
That is not re-derived here: the harness reports the offset and length of
every draw when it records, so the layout comes from a single probe run of the
real thing.
"""

import logging

from itertools import combinations

from z3 import (
    BitVecNumRef,
    BitVecRef,
    BoolRef,
    ExprRef,
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

# Ceiling on the solver calls `observability` spends working out which of its
# constraints a path admits. One per candidate constraint, on a formula that
# is already known satisfiable, so this is only a guard against a pathological
# number of tagged bytes.
MAX_OBSERVABILITY_CHECKS = 256

# Width of the region tag in a pattern byte. The high nibble names the buffer
# and the low nibble the index within it, which fits the char arrays these
# tests generate; a region of more than 15 elements repeats the low nibble,
# and bytes that share one are simply back to being indistinguishable from
# each other -- still not from the other region.
REGION_TAG_BITS = 4


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


def _element(name: str) -> tuple[str, int] | None:
    """The region and index a drawn array element belongs to, if it is one.

    `sym_var_array("src", 3, 8)` reaches the formula as `src_3`, and that is
    the only shape an element takes. A scalar has no index, which is what
    keeps `len` out of this: the whole point is to leave the arguments a path
    reasons about free and fix only the bytes it does not.
    """
    region, _, index = name.rpartition('_')

    if not region or not index.isdigit():
        return None

    return region, int(index)


def regions(declared: dict) -> dict[str, list[tuple[int, ExprRef]]]:
    """The drawn array elements, grouped by the buffer they belong to.

    Regions of one element are dropped. A lone `foo_2` is more likely a scalar
    that happens to end in a digit than a one-element array, and pinning a
    scalar would take away a value the path should be choosing.
    """
    from .sample_check import is_input

    grouped: dict[str, list[tuple[int, ExprRef]]] = {}

    for name, var in declared.items():
        if not is_input(name) or not is_bv(var):
            continue

        element = _element(name)
        if element is None:
            continue

        region, index = element
        grouped.setdefault(region, []).append((index, var))

    return {
        region: sorted(elements, key=lambda pair: pair[0])
        for region, elements in grouped.items()
        if len(elements) > 1
    }


def pattern_value(tag: int, index: int, bits: int) -> int:
    """The value an element is filled with: where it came from, and from where.

    Both halves earn their place. The region tag is what makes a byte that was
    never copied distinguishable from one that was; the index is what makes a
    byte copied from the *wrong* place legible, since reading 0x13 where 0x14
    belongs says "one short" on its own rather than merely "wrong".

    Tags start at 1 because 0 is what an untouched buffer already holds, and a
    pattern colliding with the initial contents is the one that cannot
    distinguish anything.
    """
    low = (1 << REGION_TAG_BITS) - 1
    value = ((tag & low) << REGION_TAG_BITS) | (index & low)

    return value & ((1 << bits) - 1)


def pattern(declared: dict) -> list[BoolRef]:
    """Fill every drawn buffer with bytes that name their own origin.

    Emitted region by region, in name order, so the tags are the same on every
    run and a partial application keeps whole buffers rather than a scatter of
    bytes across all of them.
    """
    out: list[BoolRef] = []

    for tag, (_, elements) in enumerate(
        sorted(regions(declared).items()), start=1
    ):
        for index, var in elements:
            out.append(var == pattern_value(tag, index, var.size()))

    return out


def distinctness(declared: dict) -> list[BoolRef]:
    """Weaker than `pattern`: two regions merely differ at the same index.

    What a path that constrains buffer contents itself leaves room for. A
    summary that must see a NUL at `src_3` cannot take the pattern there, but
    it can still be asked for a `dest_3` that is not also NUL -- and that
    alone is enough for a byte the summary failed to copy to be visible.
    """
    grouped = regions(declared)
    out: list[BoolRef] = []

    for left, right in combinations(sorted(grouped), 2):
        counterpart = dict(grouped[right])

        for index, var in grouped[left]:
            other = counterpart.get(index)

            if other is not None and other.size() == var.size():
                out.append(var != other)

    return out


def observability(
    formula: BoolRef, limit: int = MAX_OBSERVABILITY_CHECKS
) -> list[BoolRef]:
    """The strongest set of observability constraints `formula` still admits.

    Tried one at a time and kept only while the conjunction stays satisfiable,
    rather than all or nothing: a path that fixes one byte -- a string
    function's terminator, say -- would otherwise cost every other byte its
    constraint too, and for string summaries that is most of them.

    The pattern is preferred and distinctness picks up what it could not have,
    since a byte a path has already fixed can still be required to differ from
    its counterpart in another buffer.

    Returned rather than asserted. These constraints say which of the inputs a
    path admits is worth *sampling*, and an input they rule out is still a
    boundary worth trying, so the caller applies them as assumptions it can
    fall back from.
    """
    from .sample_check import declared_vars

    declared = declared_vars(formula)
    wanted = pattern(declared) + distinctness(declared)

    if not wanted:
        return []

    solver = Solver()
    solver.add(formula)

    # An unsatisfiable path has no models to make observable, and every check
    # below would agree without saying anything.
    if solver.check() != sat:
        return []

    kept: list[BoolRef] = []

    for spent, constraint in enumerate(wanted):
        if spent >= limit:
            logger.debug("Observability ceiling of %d check(s) reached", limit)
            break

        # Assumptions rather than assertions: a constraint that does not fit
        # has to leave no trace, and `kept` is what has fitted so far.
        if solver.check(*kept, constraint) == sat:
            kept.append(constraint)

    logger.debug(
        "Observability: %d of %d constraint(s) admitted by the path",
        len(kept), len(wanted),
    )

    return kept


def model_with(solver: Solver, extra: list):
    """A model satisfying `extra` if the solver admits one, else any model.

    The fallback is the point. An input the observability constraints
    contradict is still an input the summary admits, and refusing to sample it
    to keep the bytes tidy would trade a whole path for a byte.
    """
    if extra and solver.check(*extra) == sat:
        return solver.model()

    if solver.check() == sat:
        return solver.model()

    return None


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

    # Worked out once, against the formula as a whole. A candidate that
    # contradicts them falls back per model rather than recomputing which
    # bytes it could have kept: the point of a candidate is the boundary it
    # pins, and a boundary is worth more than a legible buffer.
    observable = observability(formula)

    # One model of the summary as a whole: somewhere it admits.
    model = model_with(solver, observable)
    if model is not None:
        record(model)

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

            model = model_with(solver, observable)
            if model is not None:
                record(model)

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
