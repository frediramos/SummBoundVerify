import logging

from dataclasses import dataclass, field
from enum import Enum

from z3 import BoolRef, ExprRef, Or, Solver, sat, unsat
from z3.z3util import get_vars

logger = logging.getLogger(__name__)


class Verdict(Enum):
    """What the summary had to say about one concrete sample."""

    matched = 'matched'        # the summary admits this input/output pair
    uncovered = 'uncovered'    # no path of the summary covers this input
    mismatched = 'mismatched'  # a path covers it, but not with this result
    skipped = 'skipped'        # nothing to compare

    @property
    def is_finding(self) -> bool:
        return self in (Verdict.uncovered, Verdict.mismatched)


@dataclass
class Check:
    """One sample's verdict, with enough context to act on it."""

    verdict: Verdict
    sample: object
    reason: str = ''
    bindings: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            'verdict': self.verdict.value,
            'reason': self.reason,
            'bindings': {k: hex(v) for k, v in self.bindings.items()},
            'sample': self.sample.as_dict(),  # type: ignore[attr-defined]
        }


def summary_formula(formulas: list) -> BoolRef | None:
    """The summary's paths as one formula: their disjunction.

    Returns None when there is nothing to check against, which is not the same
    as an unsatisfiable summary -- it means the symbolic run stored no path,
    and every sample would otherwise be reported as uncovered.
    """
    if not formulas:
        return None

    if len(formulas) == 1:
        return formulas[0]

    return Or(formulas)


def declared_vars(formula: ExprRef) -> dict[str, ExprRef]:
    """The formula's free variables, by name.

    Taken from the formula rather than rebuilt from the sample, so the widths
    are whatever the symbolic run actually used. Building `BitVec(name, bits)`
    from the sample's own width instead would produce a *different* variable
    whenever the two sides disagree -- and Z3 would not complain, it would
    just quietly leave the real one unconstrained.
    """
    return {v.decl().name(): v for v in get_vars(formula)}


def is_input(name: str) -> bool:
    """Whether a formula variable stands for something the harness draws.

    `Ret` and the `mem_*` bytes are outputs: they are what the summary claims
    about a run, not what the run was given.
    """
    return name != 'Ret' and not name.startswith('mem_')


def _bind(var: ExprRef, value: int, bits: int, name: str) -> BoolRef | None:
    """Pin `var` to `value`, or refuse if the two sides disagree on width.

    A width mismatch means the halves were built for different architectures:
    a `size_t` sampled as 8 bytes cannot be checked against one reasoned about
    as 4. Silently truncating would turn that into wrong verdicts.
    """
    width = var.size()

    if width != bits:
        raise ValueError(
            f"{name} is {bits} bits in the sample but {width} in the "
            f"summary's formula. The sampling harness and the symbolic run "
            f"must be built for the same architecture."
        )

    # Z3 coerces the int to a bitvector of the variable's own sort, so the
    # unsigned reading the sample carries wraps to the same bits the target
    # had in memory.
    return var == value


def input_bindings(declared: dict, sample) -> tuple[list, dict]:
    """Pin the sample's arguments to the formula's own variables.

    Returns the constraints and, separately, the values behind them, because a
    finding is only actionable if it says which input produced it.

    An argument the formula never mentions is dropped rather than reported: a
    summary may legitimately ignore an input the concrete function draws.
    """
    bindings = []
    values = {}

    for name, value in sample.inputs.items():
        var = declared.get(name)
        if var is None:
            continue

        bindings.append(_bind(var, value.value, value.bits, name))
        values[name] = value.value

    return bindings, values


def _memory_bindings(sample, declared: dict) -> list:
    """Pin the tagged regions, byte by byte.

    get_cnstr lifts each region into one 8-bit variable per byte, named
    `mem_<region>_<index>`, so a region recorded as a blob has to be taken
    apart to match.
    """
    bindings = []

    for name, value in sample.memory.items():
        for index, byte in enumerate(value.raw):
            var = declared.get(f'mem_{name}_{index}')
            if var is None:
                continue
            bindings.append(var == byte)

    return bindings


def check_sample(formula: BoolRef, sample) -> Check:
    """Does the summary admit this sample?"""
    if sample.rejected:
        return Check(
            Verdict.skipped, sample,
            "the test's own assumptions turned this input away",
        )

    declared = declared_vars(formula)
    inputs, bindings = input_bindings(declared, sample)

    solver = Solver()
    solver.add(formula)

    # Does any path cover this input at all?
    solver.push()
    solver.add(inputs)

    if solver.check() == unsat:
        solver.pop()
        return Check(
            Verdict.uncovered, sample,
            "no path of the summary covers this input",
            bindings,
        )

    # It does. Can it produce what the function produced?
    outputs = _memory_bindings(sample, declared)

    ret = declared.get('Ret')
    pointer_return = getattr(sample, 'ret_is_pointer', False)

    if sample.ret is not None and ret is not None and not pointer_return:
        outputs.append(_bind(ret, sample.ret.value, sample.ret.bits, 'Ret'))
        bindings['Ret'] = sample.ret.value

    if not outputs:
        solver.pop()

        # A pointer return with nothing tagged leaves nothing comparable, and
        # saying so is the whole point: reporting a pass here would claim the
        # summary survived a check that never happened.
        reason = (
            "the function returns an address, which means nothing across "
            "runs, and no memory was tagged to compare instead -- run with "
            "-memory to check what it wrote"
            if pointer_return else
            "the summary constrains nothing observable for this input"
        )

        return Check(Verdict.skipped, sample, reason, bindings)

    solver.add(outputs)
    result = solver.check()
    solver.pop()

    if result == sat:
        return Check(Verdict.matched, sample, '', bindings)

    return Check(
        Verdict.mismatched, sample,
        "the summary covers this input but cannot produce this result",
        bindings,
    )


def formula_key(test: str) -> str:
    """The store's name for a test's formulas.

    The two sides spell the same test differently: the generated code calls it
    `test_1` (that is the C function's name, which the sampler records), while
    `store_cnstr` was given `summ_test1`. Joining on the unconverted name finds
    nothing and reports every sample as unchecked -- a silent pass.
    """
    return f'summ_{test.replace("_", "")}'


def check_samples(constraints: dict, samples: list) -> dict[str, list[Check]]:
    """Check every sample against the formulas of the test that produced it.

    `constraints` is keyed `summ_test1`, `summ_test2`, ... and samples carry
    the test they came from, so the two are joined per test rather than
    checking everything against the first formula found.
    """
    checks: dict[str, list[Check]] = {}

    for sample in samples:
        test = sample.test or 'test_1'
        formulas = constraints.get(formula_key(test))

        formula = summary_formula(formulas or [])

        if formula is None:
            checks.setdefault(test, []).append(Check(
                Verdict.skipped, sample,
                f"no summary formula was stored for {test}",
            ))
            continue

        checks.setdefault(test, []).append(check_sample(formula, sample))

    return checks


def report(checks: dict[str, list[Check]]) -> dict:
    """Fold the per-sample verdicts into something worth printing.

    A single mismatch refutes the summary; passing is always provisional,
    since it only says no sampled input contradicted it.
    """
    out = {}

    for test, results in checks.items():
        counts = {v.value: 0 for v in Verdict}
        for check in results:
            counts[check.verdict.value] += 1

        findings = [c for c in results if c.verdict.is_finding]

        if findings:
            verdict = findings[0].verdict.value
        elif counts[Verdict.matched.value]:
            verdict = 'passed'
        else:
            verdict = 'starved'

        out[test] = {
            'verdict': verdict,
            'counts': counts,
            'checked': len(results),
            'findings': [c.as_dict() for c in findings],
        }

    return out
