"""Sampling the concrete function with AFL++.

Counterpart to `angrEngine`, but not its mirror image. The symbolic engine
executes both the summary and the concrete function and proves an implication
between them. This one never touches the summary: it compiles the concrete
function on its own, lets AFL++ explore it, and writes down what it returned
for the inputs it was given.

The result is a set of `(input, output)` pairs. What makes them useful is that
they are named the same way the summary's symbolic run names its variables --
`n` for a scalar, `str_0` for an array element -- so a pair can be matched
against the formula angr produced without either side knowing about the other.

AFL++ is an input *generator* here, not an oracle. Recording every execution
of a campaign would cost far more than it is worth when the fuzzer is about to
discard nearly all of them; what is worth keeping is its queue, which is the
deduplicated, coverage-diverse set it settled on. So the campaign runs with no
output at all, and the queue is replayed afterwards in recording mode.

Builds at -m32 by default, matching the symbolic engine's word size. This is
not cosmetic: a `size_t` that is 8 bytes here and 4 there would make every
sample of it unmatchable against the formula.
"""

import json
import logging
import os
import re
import shutil
import struct
import subprocess as sp

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from summboundverify.exceptions import CompilationError, RunError

from summboundverify.validation_gen.concrete import (
    CONCRETE_DIR,
    DRIVER_SOURCE,
    SAMPLER_SOURCE,
    SAMPLER_HEADER,
    TEST_ENTRY,
)

logger = logging.getLogger(__name__)

Arch = Literal['x86', 'x64']

FLOAT_SEEDS = {
    'zero': 0.0,
    'neg_zero': -0.0,
    'one': 1.0,
    'neg_one': -1.0,
    'half': 0.5,
    'two': 2.0,
    'inf': float('inf'),
    'neg_inf': float('-inf'),
    'nan': float('nan'),
}

AFL_CC = 'afl-clang-fast'
AFL_FUZZ = 'afl-fuzz'

STATS_RE = re.compile(
    r'execs=(?P<execs>\d+)\s+rejected=(?P<rejected>\d+)'
    r'(?:\s+exited=(?P<exited>\d+))?'
)
AFL_EXECS_RE = re.compile(r'execs_done\s*:\s*(?P<execs>\d+)')


def afl_available() -> bool:
    return bool(shutil.which(AFL_CC) and shutil.which(AFL_FUZZ))


def _le_int(raw: bytes) -> int:
    """The bytes as the unsigned integer the target would read them as."""
    return int.from_bytes(raw, byteorder='little', signed=False)


@dataclass
class Value:
    """One named quantity, kept as bytes first and a number second.

    The bytes are what the target had in memory, unconverted. That ordering
    matters for floating point, where the bit pattern *is* the value under
    test and any arithmetic reading of it would be a different value.
    """

    bits: int
    raw: bytes

    # Where this value was drawn from, for inputs: the offset and length of
    # the tape bytes the harness consumed. A seed generator needs both to put
    # a chosen value where the draw will pick it up. Zero-length for anything
    # that did not come off the tape (a return value, a memory region).
    offset: int = 0
    length: int = 0

    @property
    def value(self) -> int:
        return _le_int(self.raw)

    def as_dict(self) -> dict:
        return {'bits': self.bits, 'bytes': self.raw.hex(), 'value': self.value}


@dataclass
class Sample:
    """What one execution of one test did.

    `inputs` is keyed the way the symbolic side names its variables, so it
    joins to a formula directly. `rejected` marks a run the test's own
    assumptions turned away -- it carries no return value and proves nothing,
    which is different from a run that produced one.
    """

    test: str
    tape: bytes
    rejected: bool = False
    inputs: dict[str, Value] = field(default_factory=dict)
    memory: dict[str, Value] = field(default_factory=dict)
    ret: Value | None = None

    def as_dict(self) -> dict:
        return {
            'test': self.test,
            'tape': self.tape.hex(),
            'rejected': self.rejected,
            'inputs': {k: v.as_dict() for k, v in self.inputs.items()},
            'memory': {k: v.as_dict() for k, v in self.memory.items()},
            'ret': self.ret.as_dict() if self.ret else None,
        }


class aflEngine():

    def __init__(
        self,
        testfile: str | Path,
        libs: list[str] | list[Path] | None = None,
        arch: Arch = 'x86',
        execs: int = 10000,
        tape: int = 64,
        timeout: int | None = 30 * 60,
        results_dir: str | Path = '.',
        constraints: dict | None = None,
    ):
        if not afl_available():
            raise RunError(
                f"Sampling requires AFL++: {AFL_CC} and {AFL_FUZZ} must be on "
                f"PATH (Debian/Ubuntu: apt install afl++). Building 32-bit "
                f"targets additionally needs gcc-multilib and libc6-dev-i386."
            )

        self.testfile = Path(testfile)
        self.libs = [Path(lib) for lib in (libs or [])]
        self.arch = arch
        self.execs = execs
        self.tape = tape
        self.timeout = timeout
        self.results_dir = Path(results_dir)

        # The summary's formulas, when they are already known. Used to seed
        # the campaign at the boundaries the summary actually has, which the
        # fuzzer cannot see: it measures coverage of the concrete function.
        self.constraints = constraints or {}

        self.binary = self.testfile.with_suffix('.fuzz')
        self.workdir = self.testfile.parent / f'{self.testfile.stem}.aflwork'

        self.samples: list[Sample] = []
        self.crashes: list[Path] = []

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------

    def _cflags(self) -> list[str]:
        flags = [
            '-O1', '-g',
            '-I', str(CONCRETE_DIR),

            # Force the sampler's declarations into every translation unit,
            # the generated harness included. Without visible prototypes the
            # calls go through the default argument promotions and a `char`
            # reaching a wider parameter leaves the upper bits undefined.
            '-include', str(SAMPLER_HEADER),

            # The generated test defines main(); the driver owns the real one.
            f'-Dmain={TEST_ENTRY}',

            # A target calling exit() would take the harness down with it and
            # AFL++ would read the dead process as a crash. sbv_exit discards
            # the run instead. sbv_sample.c and driver.c #undef this.
            '-Dexit=sbv_exit',

            '-Wno-int-conversion',
            '-Wno-unused-variable',
            '-fno-builtin',
        ]

        if self.arch == 'x86':
            flags.append('-m32')
            # At -m32 an implicit `int` declaration is the same width as every
            # return type in play, so the calls the generated test makes into
            # helper libraries (lib.c declares no prototypes) are harmless.
            # Clang 16+ makes this an error by default, hence -Wno-error.
            flags.append('-Wno-error=implicit-function-declaration')
        else:
            # At x64 an implicitly declared function returns int and a wider
            # return value is silently truncated -- which would be recorded as
            # the concrete function's answer and blamed on the summary.
            flags.append('-Werror=implicit-function-declaration')

        return flags

    def compile(self) -> Path:
        cmd = [
            AFL_CC,
            *self._cflags(),
            str(self.testfile),
            str(SAMPLER_SOURCE),
            str(DRIVER_SOURCE),
            *[str(lib) for lib in self.libs],
            '-o', str(self.binary),
        ]

        logger.info("Compiling sampling harness:\n %s", ' '.join(cmd))
        result = sp.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            if self.arch == 'x86' and (
                'bits/' in result.stderr or '-m32' in result.stderr
            ):
                raise CompilationError(
                    "32-bit toolchain missing. Sampling defaults to -m32 to "
                    "match the symbolic engine's word size; install "
                    "gcc-multilib and libc6-dev-i386, or pass --compile x64 "
                    "(note that the samples are then only comparable against "
                    "a 64-bit symbolic run).\n\n" + result.stderr,
                    ' '.join(cmd)
                )
            raise CompilationError(result.stderr, ' '.join(cmd))

        if result.stderr:
            logger.warning(result.stderr)

        return self.binary

    # ------------------------------------------------------------------
    # Exploration
    # ------------------------------------------------------------------

    def _seed_corpus(self) -> Path:
        """Seed inputs biased towards what bounded arguments need.

        AFL++ discovers the rest, but starting from all-zero and small-value
        tapes gets past the input assumptions immediately instead of spending
        the first minutes being rejected.

        The float seeds matter for a different reason. Byte-oriented seeds
        read as doubles are almost all denormal junk (1.18e-303 and the like),
        so a campaign over a floating-point argument spends its budget nowhere
        near the values that actually distinguish implementations -- zero,
        one, the halves, the infinities and the NaNs.
        """
        indir = self.workdir / 'seeds'
        indir.mkdir(parents=True, exist_ok=True)

        (indir / 'zeros').write_bytes(bytes(self.tape))
        (indir / 'small').write_bytes(
            bytes(range(1, 8)) * (self.tape // 7 + 1)
        )
        (indir / 'mixed').write_bytes(
            bytes((i * 7) & 0x0f for i in range(self.tape))
        )

        for name, value in FLOAT_SEEDS.items():
            tape = struct.pack('<d', value) * (self.tape // 8 + 1)
            (indir / f'f64_{name}').write_bytes(tape[:self.tape])

        for i, tape in enumerate(self._formula_seeds()):
            (indir / f'summ_{i:03d}').write_bytes(tape)

        return indir

    def _probe(self) -> Sample | None:
        """One recorded run, to learn where each argument sits on the tape.

        Taken from the harness itself rather than worked out from the
        generated source: the layout is a property of how the draws execute,
        and the harness is the thing that executes them.
        """
        probe = self.workdir / 'probe'
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_bytes(bytes(self.tape))

        samples = self._record(probe)
        return samples[0] if samples else None

    def _formula_seeds(self) -> list[bytes]:
        """Seeds aimed at the summary's own branches and boundaries."""
        if not self.constraints:
            return []

        from .sample_check import formula_key
        from .seeding import seed_tapes

        sample = self._probe()
        if sample is None:
            logger.debug("Probe recorded nothing; no formula-derived seeds")
            return []

        formulas = self.constraints.get(formula_key(sample.test or 'test_1'))

        tapes = seed_tapes(formulas or [], sample, self.tape)

        if tapes:
            logger.info(
                "Seeded %d input(s) from the summary's path conditions",
                len(tapes),
            )

        return tapes

    def _afl_env(self) -> dict:
        env = dict(os.environ)
        env.update({
            'AFL_SKIP_CPUFREQ': '1',
            'AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES': '1',
            'AFL_NO_UI': '1',
            'SBV_STATS_FILE': str((self.workdir / 'stats').resolve()),
        })
        return env

    def explore(self) -> Path:
        """Let AFL++ build a corpus over the concrete function.

        Returns the queue directory. Nothing is recorded here: the campaign is
        search, and the search is worth keeping only in the shape of the
        inputs it settled on.
        """
        indir = self._seed_corpus()
        outdir = self.workdir / 'out'

        cmd = [
            AFL_FUZZ,
            '-i', str(indir.resolve()),
            '-o', str(outdir.resolve()),
            '-E', str(self.execs),
            '--', str(self.binary.resolve()),
        ]

        logger.info("Running AFL++:\n %s", ' '.join(cmd))

        try:
            result = sp.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout, env=self._afl_env(),
            )
        except sp.TimeoutExpired:
            raise RunError(f"Fuzzing timed out after {self.timeout} seconds")

        if result.returncode != 0:
            raise RunError(
                f"{AFL_FUZZ} exited with {result.returncode}:\n"
                f"{result.stdout[-2000:]}\n{result.stderr[-2000:]}"
            )

        # A crash is a bug in the concrete function, not evidence about the
        # summary. Worth surfacing, but it is not a sample: the run produced
        # no return value to compare.
        self.crashes = sorted(
            (outdir / 'default' / 'crashes').glob('id:*')
        )

        return outdir / 'default' / 'queue'

    def _tapes(self, queue: Path) -> list[Path]:
        """The tapes to record, best-effort.

        Normally AFL++'s queue, which already contains the seeds it kept. If
        the campaign never got that far, the seeds themselves still describe
        the function at a handful of points, and a few samples beat none.
        """
        tapes = sorted(queue.glob('id:*')) if queue.is_dir() else []

        if tapes:
            return tapes

        logger.warning(
            "AFL++ produced no queue; recording the seed corpus instead"
        )
        return sorted((self.workdir / 'seeds').iterdir())

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def _record(self, tape: Path) -> list[Sample]:
        """Run one tape in recording mode and parse what it produced."""
        cmd = [str(self.binary.resolve()), '--record', str(tape.resolve())]

        try:
            result = sp.run(cmd, capture_output=True, text=True, timeout=60)
        except sp.TimeoutExpired:
            logger.warning("Recording %s timed out; skipped", tape.name)
            return []

        if result.returncode != 0:
            logger.warning(
                "Recording %s exited with %d; skipped",
                tape.name, result.returncode,
            )
            return []

        return self._parse(result.stdout, tape.read_bytes())

    def _parse(self, stdout: str, tape: bytes) -> list[Sample]:
        """Decode the harness's line format into samples.

        Lines accumulate into the sample they belong to and `E` closes it, so
        an array element is recorded before the test that owns it is known to
        have finished. See sbv_sample.c for the format.
        """
        samples: list[Sample] = []
        current = Sample(test='', tape=tape)

        for line in stdout.splitlines():
            parts = line.split()
            if not parts:
                continue

            kind, parts = parts[0], parts[1:]

            if kind == 'V' and len(parts) == 6:
                name, index, bits, offset, length, raw = parts
                # An indexed draw is one element of an array, and the symbolic
                # side calls it `<name>_<index>`. Matching that here is what
                # lets a sample be joined to a formula by name alone.
                key = name if index == '-' else f'{name}_{index}'
                current.inputs[key] = Value(
                    int(bits), bytes.fromhex(raw), int(offset), int(length)
                )

            elif kind == 'M' and len(parts) == 3:
                name, nbytes, raw = parts
                current.memory[name] = Value(
                    int(nbytes) * 8, bytes.fromhex(raw)
                )

            elif kind == 'R' and len(parts) == 2:
                bits, raw = parts
                current.ret = Value(int(bits), bytes.fromhex(raw))

            elif kind == 'E':
                if parts and parts[0] == 'rejected':
                    current.rejected = True
                else:
                    current.test = parts[1] if len(parts) > 1 else 'test_1'

                samples.append(current)
                current = Sample(test='', tape=tape)

        return samples

    def collect(self, queue: Path) -> list[Sample]:
        """Replay every tape and keep the distinct pairs.

        Different tapes routinely draw the same arguments -- AFL++ keeps an
        input for the coverage it reaches, and the float seeds all begin with
        zero bytes, so a plain replay of the queue is mostly repeats. The
        function under test is deterministic, so a repeated input can only
        produce a repeated output: keeping it would inflate the sample count
        without checking the summary anywhere new.
        """
        samples: list[Sample] = []
        seen: set[tuple] = set()

        for tape in self._tapes(queue):
            for sample in self._record(tape):
                key = (
                    sample.test,
                    sample.rejected,
                    tuple(sorted(
                        (name, value.raw)
                        for name, value in sample.inputs.items()
                    )),
                )

                if key in seen:
                    continue

                seen.add(key)
                samples.append(sample)

        return samples

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def _stats(self) -> tuple[int, int, int]:
        """Executions, rejections and exits, as counted by the harness.

        These cover only the most recent forked process -- the persistent loop
        restarts and rewrites the file -- so they are a *sample* of the
        rejection behaviour, not campaign totals. The campaign total comes
        from AFL++ itself.
        """
        stats = self.workdir / 'stats'

        if not stats.exists():
            return 0, 0, 0

        match = STATS_RE.search(stats.read_text())
        if not match:
            return 0, 0, 0

        return (
            int(match.group('execs')),
            int(match.group('rejected')),
            int(match.group('exited') or 0),
        )

    def _afl_execs(self) -> int:
        stats = self.workdir / 'out' / 'default' / 'fuzzer_stats'

        if not stats.exists():
            return 0

        match = AFL_EXECS_RE.search(stats.read_text())
        return int(match.group('execs')) if match else 0

    def _write_results(self) -> Path:
        """Emit the samples, grouped by the test that produced them.

        Keyed like the symbolic engine's results so a `both` run can line the
        two up, and carrying the counts a reader needs to judge how much the
        campaign established -- samples that were all rejected prove nothing,
        however many there are.
        """
        sampled, rejected, exited = self._stats()
        usable = [s for s in self.samples if not s.rejected]

        by_test: dict[str, list[dict]] = {}
        for sample in self.samples:
            key = sample.test or 'test_1'
            by_test.setdefault(key, []).append(sample.as_dict())

        results = {
            f'{self.testfile.stem}.{test}': {
                'fuzz': {
                    'samples': samples,
                    'usable': sum(1 for s in samples if not s['rejected']),
                    'execs': self._afl_execs(),
                    'rejection_rate': round(
                        rejected / sampled, 4
                    ) if sampled else 0.0,
                    'sampled_execs': sampled,
                    'sampled_rejected': rejected,
                    'sampled_exited': exited,
                    'crashes': [c.name for c in self.crashes],
                }
            }
            for test, samples in by_test.items()
        }

        self.results_dir.mkdir(parents=True, exist_ok=True)
        out = self.results_dir / f'{self.binary.name}_result.json'
        out.write_text(json.dumps(results, indent=2))

        logger.info(
            "Recorded %d sample(s), %d usable, from %d execs -> %s",
            len(self.samples), len(usable), self._afl_execs(), out,
        )

        return out

    def run(self) -> Path:
        self.compile()
        queue = self.explore()
        self.samples = self.collect(queue)

        usable = [s for s in self.samples if not s.rejected]
        sampled, rejected, exited = self._stats()

        if not usable:
            logger.warning(
                "Every recorded input was turned away (%d rejected, %d of "
                "them by calling exit(), out of %d sampled): nothing was "
                "sampled to check the summary against. Widen the input "
                "bounds or seed the corpus.",
                rejected, exited, sampled,
            )

        if self.crashes:
            logger.warning(
                "The concrete function crashed on %d input(s). That is a bug "
                "in the function under test, not evidence about the summary, "
                "and those runs produced no sample.",
                len(self.crashes),
            )

        return self._write_results()
