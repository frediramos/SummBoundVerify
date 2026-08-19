"""Validating a summary by sampling, end to end.

The two halves of a fuzzing run and the check that joins them, in one call.
Lives here rather than in `main` because it has two callers with nothing else
in common: the CLI, and summer's refinement loop.

    summary (symbolic, angr)  ->  one formula per path
    concrete (native, AFL++)  ->  concrete (input, output) pairs
    guided                    ->  one more pair per path nothing reached
    check                     ->  does the summary admit each pair?

Both halves must be built for the same word size. The API stubs typedef
`size_t` as `unsigned int`, so the symbolic side is 32-bit whatever the
architecture, and only a 32-bit sampler is comparable against it.
"""

import logging

from pathlib import Path
from typing import Literal

from z3 import simplify

from summboundverify.validation_gen import CCompiler

from .engine import angrEngine
from .fuzz_engine import aflEngine
from .guided import MAX_ROUNDS, top_up
from .sample_check import check_samples, report, test_name

logger = logging.getLogger(__name__)

Arch = Literal['x86', 'x64']


def summary_formulas(
    summary_test: Path,
    libs: list | None = None,
    arch: Arch = 'x86',
    timeout: int | None = None,
    results_dir: str | Path = '.',
) -> dict:
    """Execute the summary symbolically and keep what it proved.

    Returns the formulas by the name the test stored them under -- the same
    thing a `both` run gets for free from its symbolic pass, which is why this
    is separable.
    """
    binary = summary_test.with_suffix('.test')
    CCompiler(arch, summary_test, binary, [str(lib) for lib in (libs or [])]).compile()

    engine = angrEngine(
        str(binary), timeout=timeout, results_dir=str(results_dir),
    )
    engine.run()

    log_constraints(engine.constraints)

    return engine.constraints


def format_constraints(constraints: dict) -> str:
    """The summary's path conditions, laid out one path at a time.

    Symbolic execution prints the equivalent as part of its verdict ("Summary
    Constraints"); sampling checks every sample against these same formulas
    and showed none of them, which leaves a finding hard to act on -- the
    input that broke the summary is reported, but not what the summary
    claimed about it.

    Per path rather than as their disjunction, because that is the
    granularity the rest of the run works at: seeding aims at one path, and
    guided sampling counts the paths nothing reached.
    """
    blocks = []

    for key, formulas in constraints.items():
        if not formulas:
            continue

        paths = [
            '\t[{}] {}'.format(
                index, str(simplify(formula)).replace('\n', '\n\t    ')
            )
            for index, formula in enumerate(formulas, start=1)
        ]

        blocks.append(
            f'==> Summary Constraints ({test_name(key)}, '
            f'{len(formulas)} path(s)):\n\n' + '\n\n'.join(paths)
        )

    return '\n\n'.join(blocks)


def log_constraints(constraints: dict) -> None:
    """Show what the summary says, before anything is checked against it."""
    text = format_constraints(constraints)

    if not text:
        logger.warning(
            "The summary's symbolic run stored no path condition: there is "
            "nothing for the samples to be checked against."
        )
        return

    logger.info('\n' + text)


def validate_by_sampling(
    concrete_test: Path,
    constraints: dict,
    libs: list | None = None,
    arch: Arch = 'x86',
    execs: int = 10000,
    timeout: int | None = None,
    results_dir: str | Path = '.',
    guided: int = MAX_ROUNDS,
) -> tuple[dict, list]:
    """Sample the concrete function and check the samples against `constraints`.

    Returns the per-test report and the samples behind it. The report is the
    thing to act on; the samples are kept because a refinement loop wants the
    input that broke the summary, not just the verdict.

    `guided` bounds the rounds spent constructing inputs for summary paths the
    campaign never exercised; zero leaves the campaign's own corpus untouched.
    """
    engine = aflEngine(
        concrete_test,
        libs=libs,
        arch=arch,
        execs=execs,
        timeout=timeout,
        results_dir=results_dir,
        constraints=constraints,
    )
    engine.run()

    if guided and constraints:
        extra = top_up(engine, constraints, engine.samples, rounds=guided)

        if extra:
            engine.samples = engine.samples + extra
            engine.write_results()

    return report(check_samples(constraints, engine.samples)), engine.samples


def write_report(results: dict, out: Path) -> Path:
    import json

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    return out


def log_report(results: dict) -> None:
    """Say what the check established, and what it did not."""
    for test, entry in results.items():
        counts = entry['counts']

        if entry['verdict'] == 'passed':
            logger.info(
                "%s: %d sample(s) admitted by the summary. Sampling cannot "
                "certify -- this says no sampled input contradicted it.",
                test, counts['matched'],
            )

        elif entry['verdict'] == 'starved':
            logger.warning(
                "%s: nothing was checked. Every sample was turned away or "
                "the summary constrains nothing observable.", test,
            )

        else:
            first = entry['findings'][0]
            logger.error(
                "%s: %s -- %s\n  %s",
                test, entry['verdict'], first['reason'], first['bindings'],
            )
