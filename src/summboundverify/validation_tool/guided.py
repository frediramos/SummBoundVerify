"""Sampling where the fuzzer will not go: one input per unexercised path.

AFL++ chooses inputs by coverage of the *concrete* function, and the summary's
cases need not line up with the function's branches at all. A summary that
distinguishes three ranges of an argument the function treats uniformly gets
one input from the campaign and two paths nothing ever tried -- and a path no
sample reaches is a path no sample can contradict. That is a silent gap, not a
visible one: the run reports `passed`.

Seeding (`seeding.py`) anticipates this before the campaign, from the constants
the formula mentions. This closes the loop afterwards, against the samples the
campaign actually produced:

    1. for each stored path of the summary, does any sample reach it?
    2. for one that has none, ask the solver for an input that does
    3. run the concrete function on that input, and record what it returned
    4. repeat, with the inputs already tried blocked, until every path has been
       reached or the budget runs out

Step 3 is what makes this more than a coverage report. The input comes from
the summary and the answer comes from the implementation, so a path the summary
invented -- one admitting inputs on which the function does something else --
is refuted by the very input built to reach it. That is the over-approximation
direction, and it is the one a coverage-guided campaign is worst at finding.

Nothing here can manufacture a finding. Every verdict still comes from
`check_sample`, run on a real execution of the real function; what this changes
is only which executions happen. An input that misses the path it was aimed at
(the tape encoding is a draw, not an assignment) is just another sample, and an
input the test's own bounds turn away is recorded as rejected, as any other
would be.
"""

import logging

from z3 import BitVecNumRef, Or, Solver, sat

from .sample_check import declared_vars, formula_key, input_bindings, is_input
from .seeding import build_tape, tape_layout

logger = logging.getLogger(__name__)

# Rounds of solve-run-recheck per test. One round already covers every open
# path it can; the rest exist because a constructed input may be rejected or
# may draw something other than what was asked for, and the next round sees
# that and asks for a different one.
MAX_ROUNDS = 3

# Ceiling on constructed inputs across all rounds and all tests. Each costs an
# execution and a solver call, and a summary needing more paths than this is
# not one a handful of extra samples will settle.
MAX_INPUTS = 32


def reaches(path, sample) -> bool:
    """Whether `path` admits this sample's input.

    The return value is deliberately left free: the question here is coverage
    of the input, not agreement about the result. A path that covers the input
    and disagrees about the result is a `mismatched` sample, which is a
    finding, and finding it is `check_sample`'s job -- not this one's.
    """
    if sample.rejected:
        return False

    declared = declared_vars(path)

    try:
        bindings, _ = input_bindings(declared, sample)
    except ValueError:
        # The two sides disagree on a width, so this sample says nothing about
        # this formula. Reporting the path as reached would suppress the one
        # input that could expose the disagreement.
        return False

    solver = Solver()
    solver.add(path)
    solver.add(bindings)

    return solver.check() == sat


def open_paths(paths: list, samples: list) -> list[int]:
    """Indices of the paths no sample reaches."""
    return [
        index for index, path in enumerate(paths)
        if not any(reaches(path, sample) for sample in samples)
    ]


def _blocking(declared: dict, assignment: dict):
    """A clause ruling out exactly this assignment of the inputs.

    Without it the solver is free to answer the same way every round: the
    formula did not change, and neither did the question.
    """
    literals = [
        declared[name] != value
        for name, value in assignment.items()
        if name in declared
    ]

    return Or(literals) if literals else None


def input_for(path, tried: list[dict]) -> dict | None:
    """An input reaching `path` and unlike every one already tried.

    Every input variable is given a value, `model_completion` included, rather
    than only those the model happens to bind. A variable the solver left free
    would otherwise be written to the tape as zero, which is a value the path
    may well exclude -- so the input would miss the path it was built for.
    """
    declared = declared_vars(path)

    solver = Solver()
    solver.add(path)

    for assignment in tried:
        clause = _blocking(declared, assignment)
        if clause is not None:
            solver.add(clause)

    if solver.check() != sat:
        return None

    model = solver.model()
    assignment = {}

    for name, var in declared.items():
        if not is_input(name):
            continue

        value = model.eval(var, model_completion=True)
        if isinstance(value, BitVecNumRef):
            assignment[name] = value.as_long()

    return assignment or None


def _layout(samples: list) -> list:
    """The tape layout, from whichever sample recorded one.

    Any sample of the test will do, rejected ones included: the draws are
    emitted as they happen, so a run turned away after reading its arguments
    still reports where they came from.
    """
    for sample in samples:
        layout = tape_layout(sample)
        if layout:
            return layout

    return []


def top_up(
    engine,
    constraints: dict,
    samples: list,
    rounds: int = MAX_ROUNDS,
    limit: int = MAX_INPUTS,
) -> list:
    """Extra samples aimed at the summary paths the campaign never reached.

    Returns only the new samples, for the caller to add to the campaign's.
    Empty when there is nothing to aim at: no stored formula, no recorded
    layout to build a tape from, or every path already reached.
    """
    from .fuzz_engine import sample_key

    by_test: dict[str, list] = {}
    for sample in samples:
        by_test.setdefault(sample.test or 'test_1', []).append(sample)

    seen = {sample_key(sample) for sample in samples}
    fresh: list = []
    budget = limit

    for test, group in sorted(by_test.items()):
        if budget <= 0:
            break

        paths = constraints.get(formula_key(test)) or []
        if not paths:
            continue

        layout = _layout(group)
        if not layout:
            logger.debug("%s: nothing recorded a tape layout", test)
            continue

        pool = list(group)
        tried: list[dict] = []
        rejected = 0

        for _ in range(rounds):
            indices = open_paths(paths, pool)

            if not indices:
                break

            produced = 0

            for index in indices:
                if budget <= 0:
                    break

                assignment = input_for(paths[index], tried)
                if assignment is None:
                    continue

                tried.append(assignment)
                budget -= 1

                tape = build_tape(layout, assignment, engine.tape)
                drawn = engine.sample_tape(tape, f'{test}-p{index}-{len(tried):03d}')

                for sample in drawn:
                    key = sample_key(sample)
                    if key in seen:
                        continue

                    seen.add(key)
                    fresh.append(sample)
                    produced += 1

                    if (sample.test or 'test_1') == test:
                        pool.append(sample)
                        rejected += sample.rejected

            # Nothing new came back, so the next round would ask the same
            # questions of the same samples and get the same answers.
            if not produced:
                break

        still_open = open_paths(paths, pool)

        if still_open:
            logger.info(
                "%s: %d of the summary's %d path(s) were never reached by any "
                "input -- nothing sampled can speak about them.",
                test, len(still_open), len(paths),
            )

        if rejected:
            # Not a finding, but not noise either: the summary describes
            # inputs the generated test refuses to produce, so part of what it
            # claims lies outside the domain being validated at all.
            logger.info(
                "%s: %d constructed input(s) were turned away by the test's "
                "own assumptions. The summary admits inputs outside the "
                "bounds the test was generated with.",
                test, rejected,
            )

    if fresh:
        logger.info(
            "Constructed %d input(s) for summary paths the campaign left "
            "unexercised", len(fresh),
        )

    return fresh
