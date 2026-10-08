import logging

from dataclasses import dataclass, field
from enum import Enum

from z3 import BoolRef, ExprRef, Or, Solver, sat
from z3.z3util import get_vars

logger = logging.getLogger(__name__)


class Verdict(Enum):
    """What the summary had to say about one concrete sample."""

    matched = 'matched'        # the summary admits this input/output pair
    mismatched = 'mismatched'  # a path covers it, but not with this result
    skipped = 'skipped'        # nothing to compare

    @property
    def is_finding(self) -> bool:
        return self == Verdict.mismatched


@dataclass
class Check:
    """One sample's verdict, with enough context to act on it."""

    verdict: Verdict
    sample: object
    reason: str = ''

    # The sample's values the check pinned in the formula, inputs first.
    bindings: dict = field(default_factory=dict)

    # The sample's values it did not: inputs the summary does not depend on,
    # observations its formula has no variable for, a pointer return.
    ignored: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            'verdict': self.verdict.value,
            'reason': self.reason,
            'bindings': {k: hex(v) for k, v in self.bindings.items()},
            'ignored': {k: hex(v) for k, v in self.ignored.items()},
            'sample': self.sample.as_dict(),  # type: ignore[attr-defined]
        }


def summary_formula(formulas: list) -> BoolRef | None:
    """The summary's paths as one formula: their disjunction.

    Returns None when there is nothing to check against, which is not the same
    as an unsatisfiable summary.
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
    return name != 'Ret' and not name.startswith('mem_') and not name.startswith('file_')


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


@dataclass
class Pins:
    """What a sample pins in the formula, and what it observed but could not.

    Every observation goes through `pin`, so the report shows exactly the
    values the check used -- and, apart, the ones it could not use -- rather
    than whichever families of variables remembered to record theirs.
    """

    declared: dict
    constraints: list = field(default_factory=list)
    values: dict = field(default_factory=dict)
    ignored: dict = field(default_factory=dict)

    def pin(self, name: str, value: int, bits: int | None = None) -> None:
        var = self.declared.get(name)

        if var is None:
            self.ignored[name] = value
            return

        if bits is None:
            self.constraints.append(var == value)
        else:
            self.constraints.append(_bind(var, value, bits, name))

        self.values[name] = value


def _pin_inputs(pins: Pins, sample) -> None:
    """The sample's arguments. One the formula never mentions is ignored, not
    an error: a summary may legitimately not depend on an input."""
    for name, value in sample.inputs.items():
        pins.pin(name, value.value, value.bits)


def input_bindings(declared: dict, sample) -> tuple[list, dict]:
    """Pin the sample's arguments to the formula's own variables.

    Returns the constraints and, separately, the values behind them, because a
    finding is only actionable if it says which input produced it.
    """
    pins = Pins(declared)
    _pin_inputs(pins, sample)
    return pins.constraints, pins.values


def _pin_memory(pins: Pins, sample) -> None:
    """The tagged regions, byte by byte.

    get_cnstr lifts each region into one 8-bit variable per byte, named
    `mem_<region>_<index>`, so a region recorded as a blob has to be taken
    apart to match.
    """
    for name, value in sample.memory.items():
        for index, byte in enumerate(value.raw):
            pins.pin(f'mem_{name}_{index}', byte)


def _pin_files(pins: Pins, sample) -> bool:
    """The tagged file paths: existence and content bytes.

    Returns True when the concrete side recorded content for a file but the
    formula declares no `file_<name>_byte_*` variables for it -- typically
    because the summary closed the fd before get_cnstr.
    """
    content_unchecked = False

    for name, fv in sample.files.items():
        pins.pin(f'file_{name}_exists', 1 if fv.exists else 0)

        before = len(pins.values)
        for index, byte in enumerate(fv.raw):
            pins.pin(f'file_{name}_byte_{index}', byte)

        if fv.raw and len(pins.values) == before:
            content_unchecked = True

    return content_unchecked


def _pin_fds(pins: Pins, sample) -> None:
    """The open descriptors: the set, then each one's flags, mode, offset,
    size and content.

    The key in sample.fds is 'fd3', 'fd4', ... -- the descriptor number,
    matching the symbolic side's 'file_fd3_flags', 'file_fd3_byte_0', etc.
    """
    # The set of open descriptors, as one variable. Per-fd variables for a
    # descriptor only one side has open would otherwise be left free, and the
    # sample admitted whatever the summary did with it.
    if sample.open_fds is not None:
        pins.pin('file_open_fds', sample.open_fds)

    for name, fdv in sample.fds.items():
        prefix = f'file_{name}'

        for attr in ('flags', 'mode', 'offset', 'size'):
            pins.pin(f'{prefix}_{attr}', getattr(fdv, attr))

        for index, byte in enumerate(fdv.raw):
            pins.pin(f'{prefix}_byte_{index}', byte)


def check_sample(formula: BoolRef, sample) -> Check:
    """Does the summary admit this sample?"""
    if sample.rejected:
        return Check(
            Verdict.skipped, sample,
            "the test's own assumptions turned this input away",
        )

    declared = declared_vars(formula)

    inputs = Pins(declared)
    _pin_inputs(inputs, sample)

    solver = Solver()
    solver.add(formula)

    # Add input restrictions
    solver.push()
    solver.add(inputs.constraints)

    # Can it produce what the function produced?
    outputs = Pins(declared)
    _pin_memory(outputs, sample)
    fs_content_unchecked = _pin_files(outputs, sample)
    _pin_fds(outputs, sample)

    pointer_return = getattr(sample, 'ret_is_pointer', False)

    if sample.ret is not None:
        if pointer_return:
            outputs.ignored['Ret'] = sample.ret.value
        else:
            outputs.pin('Ret', sample.ret.value, sample.ret.bits)

    bindings = {**inputs.values, **outputs.values}
    ignored = {**inputs.ignored, **outputs.ignored}

    if not outputs.constraints:
        solver.pop()

        if fs_content_unchecked:
            reason = (
                "a tagged file has content on disk but the summary's "
                "formula declares no byte variables for it -- the file "
                "was probably closed before get_cnstr ran"
            )
        elif pointer_return:
            reason = (
                "the function returns an address, which means nothing across "
                "runs, and no memory was tagged to compare instead -- use an "
                "argspec with 'semantic: memory' to check what it wrote"
            )
        else:
            reason = "the summary constrains nothing observable for this input"

        return Check(Verdict.skipped, sample, reason, bindings, ignored)

    solver.add(outputs.constraints)
    result = solver.check()
    solver.pop()

    if result == sat:
        return Check(Verdict.matched, sample, '', bindings, ignored)

    return Check(
        Verdict.mismatched, sample,
        "the summary does not accept this model",
        bindings,
        ignored,
    )


def formula_key(test: str) -> str:
    """The store's name for a test's formulas.

    The two sides spell the same test differently: the generated code calls it
    `test_1` (that is the C function's name, which the sampler records), while
    `store_cnstr` was given `summ_test1`. Joining on the unconverted name finds
    nothing and reports every sample as unchecked -- a silent pass.
    """
    return f'summ_{test.replace("_", "")}'


def test_name(key: str) -> str:
    """The test as the sampler spells it, from the store's name for it.

    Inverse of `formula_key`, for output alone: the sample dump and the check
    report are both keyed `test_1`, so printing a formula under `summ_test1`
    next to them would read as a different test.
    """
    stem = key.removeprefix('summ_')

    if not stem.startswith('test'):
        return stem

    return f'test_{stem.removeprefix("test")}'


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
