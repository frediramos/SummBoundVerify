"""Concrete (fuzzing) validation engine.

Counterpart to `angrEngine`. Where that one hooks the API stubs with angr
SimProcedures and reasons symbolically, this one links the generated test
against the concrete backend in `validation_gen/concrete` and runs it under
AFL++, comparing the summary's observable behaviour with the concrete
function's.

AFL++ drives the harness in persistent mode: it hands over a byte tape in
shared memory, which is exactly what `sbv_fuzz_exec` consumes. Coverage
feedback matters here rather than being a nicety -- the generated tests
constrain their inputs (`assume(_ULE_(n, MAX_NUM_1))`), and a driver that
cannot learn which bytes matter spends nearly its whole budget being
rejected.

Builds at -m32 by default, matching the symbolic engine's word size, so that
a disagreement between the two engines is a real disagreement rather than an
artefact of `size_t` changing width.

What the two engines can conclude differs, and the result JSON reflects it:
symbolic execution places a summary on the over/under/exact lattice, whereas
concrete testing can only falsify -- it reports a divergence with a
reproducing input, or that none was found within the budget.
"""

import json
import logging
import os
import re
import shutil
import subprocess as sp

from pathlib import Path
from typing import Literal

from summboundverify.exceptions import CompilationError, RunError

from summboundverify.validation_gen.concrete import (
    CONCRETE_DIR,
    RUNTIME_HEADER,
    RUNTIME_SOURCE,
    DRIVER_SOURCE,
    TEST_ENTRY,
)

logger = logging.getLogger(__name__)

Arch = Literal['x86', 'x64']

AFL_CC = 'afl-clang-fast'
AFL_FUZZ = 'afl-fuzz'

# Parses the harness's one-line summary. `report` is last so it may contain
# spaces; `inputs` needs a lookahead because a lazy `.*?` inside an optional
# group happily matches the empty string and swallows the field.
RESULT_RE = re.compile(
    r'SBV_FUZZ\s+'
    r'execs=(?P<execs>\d+)\s+'
    r'rejected=(?P<rejected>\d+)\s+'
    r'ntests=(?P<ntests>\d+)\s+'
    r'verdict=(?P<verdict>\w+)'
    r'(?:\s+test=(?P<test>\d+))?'
    r'(?:\s+inputs=(?P<inputs>.*?)(?=\s+report=|$))?'
    r'(?:\s+report=(?P<report>.*))?'
)

STATS_RE = re.compile(
    r'execs=(?P<execs>\d+)\s+rejected=(?P<rejected>\d+)'
    r'(?:\s+ntests=(?P<ntests>\d+))?'
)
AFL_EXECS_RE = re.compile(r'execs_done\s*:\s*(?P<execs>\d+)')


def afl_available() -> bool:
    return bool(shutil.which(AFL_CC) and shutil.which(AFL_FUZZ))


class fuzzEngine():

    def __init__(
        self,
        testfile: str | Path,
        libs: list[str] | list[Path] | None = None,
        arch: Arch = 'x86',
        execs: int = 10000,
        tape: int = 64,
        timeout: int | None = 30 * 60,
        results_dir: str | Path = '.',
    ):
        if not afl_available():
            raise RunError(
                f"The fuzzing engine requires AFL++: {AFL_CC} and {AFL_FUZZ} "
                f"must be on PATH (Debian/Ubuntu: apt install afl++). "
                f"Building 32-bit targets additionally needs gcc-multilib and "
                f"libc6-dev-i386."
            )

        self.testfile = Path(testfile)
        self.libs = [Path(lib) for lib in (libs or [])]
        self.arch = arch
        self.execs = execs
        self.tape = tape
        self.timeout = timeout
        self.results_dir = Path(results_dir)

        self.binary = self.testfile.with_suffix('.fuzz')
        self.workdir = self.testfile.parent / f'{self.testfile.stem}.aflwork'

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------

    def _cflags(self) -> list[str]:
        flags = [
            '-O1', '-g',
            '-I', str(CONCRETE_DIR),

            # Force the API declarations into *every* translation unit,
            # including the summary. Without visible prototypes the calls go
            # through the default argument promotions and a `char` argument
            # reaching a wider parameter leaves the upper bits undefined.
            '-include', str(RUNTIME_HEADER),

            # The generated test defines main(); the harness owns the real one.
            f'-Dmain={TEST_ENTRY}',

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
            # return value is silently truncated -- which surfaces as a bogus
            # divergence between the summary and the concrete function.
            flags.append('-Werror=implicit-function-declaration')

        return flags

    def compile(self):
        cmd = [
            AFL_CC,
            *self._cflags(),
            str(self.testfile),
            str(RUNTIME_SOURCE),
            str(DRIVER_SOURCE),
            *[str(lib) for lib in self.libs],
            '-o', str(self.binary),
        ]

        logger.info("Compiling fuzz harness:\n %s", ' '.join(cmd))
        result = sp.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            if self.arch == 'x86' and 'bits/' in result.stderr:
                raise CompilationError(
                    "32-bit toolchain missing. The fuzz engine defaults to "
                    "-m32 to match the symbolic engine's word size; install "
                    "gcc-multilib and libc6-dev-i386, or pass --compile x64 "
                    "(note that a summary re-declaring size_t as `unsigned "
                    "int` will only build at -m32).\n\n" + result.stderr,
                    ' '.join(cmd)
                )
            raise CompilationError(result.stderr, ' '.join(cmd))

        if result.stderr:
            logger.warning(result.stderr)

        return self.binary

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _seed_corpus(self) -> Path:
        """Seed inputs biased towards what bounded arguments need.

        AFL++ discovers the rest, but starting from all-zero and small-value
        tapes gets past the input assumptions immediately instead of spending
        the first minutes being rejected.
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
        return indir

    def _afl_env(self) -> dict:
        env = dict(os.environ)
        env.update({
            'AFL_SKIP_CPUFREQ': '1',
            'AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES': '1',
            'AFL_NO_UI': '1',
            # Stop as soon as a divergence is found: there is nothing to gain
            # from continuing, and the refinement loop wants the first one.
            'AFL_BENCH_UNTIL_CRASH': '1',
            'SBV_STATS_FILE': str((self.workdir / 'stats').resolve()),
        })
        return env

    def _run_afl(self) -> dict:
        indir = self._seed_corpus()
        outdir = self.workdir / 'out'

        # A divergence is signalled by abort(), which AFL++ reads as a crash.
        # If every seed diverges, AFL++ refuses to start ("we need at least
        # one valid input seed that does not crash") and the finding would be
        # lost -- precisely the case where the summary is most obviously
        # wrong. Check the seeds ourselves first.
        for seed in sorted(indir.iterdir()):
            probe = self._replay(seed)
            if probe['verdict'] in ('diverged', 'crashed'):
                logger.info(
                    "Seed input already %s; skipping the AFL++ campaign",
                    probe['verdict'],
                )
                probe['execs'] = 1
                probe['sampled'] = 1
                return probe

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

        crashes = sorted((outdir / 'default' / 'crashes').glob('id:*'))

        if crashes:
            return self._replay(crashes[0])

        if result.returncode != 0:
            raise RunError(
                f"{AFL_FUZZ} exited with {result.returncode}:\n"
                f"{result.stdout[-2000:]}\n{result.stderr[-2000:]}"
            )

        return self._no_crash_result()

    def _stats(self) -> tuple[int, int, int]:
        """Exec/rejection counts, and the test count, sampled by the harness.

        These cover only the most recent forked process (the persistent loop
        restarts and the file is rewritten), so they are a *sample* of the
        rejection behaviour, not campaign totals. The campaign total comes
        from AFL++ itself, in `_afl_execs`.
        """
        stats = self.workdir / 'stats'

        if not stats.exists():
            return 0, 0, 1

        match = STATS_RE.search(stats.read_text())
        if not match:
            return 0, 0, 1

        return (
            int(match.group('execs')),
            int(match.group('rejected')),
            int(match.group('ntests') or 1),
        )

    def _afl_execs(self) -> int:
        """Total executions, as counted by AFL++."""
        stats = self.workdir / 'out' / 'default' / 'fuzzer_stats'

        if not stats.exists():
            return 0

        match = AFL_EXECS_RE.search(stats.read_text())
        return int(match.group('execs')) if match else 0

    def _no_crash_result(self) -> dict:
        sampled, rejected, ntests = self._stats()
        execs = self._afl_execs() or sampled or self.execs

        return {
            'verdict': (
                'starved' if sampled and rejected >= sampled else 'passed'
            ),
            'execs': execs,
            'sampled': sampled,
            'rejected': rejected,
            'ntests': ntests,
            'diverged_test': None,
            'counterexample': None,
        }

    def _replay(self, tape: Path) -> dict:
        """Run one saved tape to recover a decoded counterexample."""
        cmd = [str(self.binary.resolve()), '--replay', str(tape.resolve())]

        logger.info("Replaying input:\n %s", ' '.join(cmd))
        result = sp.run(cmd, capture_output=True, text=True, timeout=60)

        if 'SBV_FUZZ' not in result.stdout:
            # The replay itself died, so the input crashes the harness rather
            # than merely diverging. Still a finding, but a different one, and
            # it must not be reported as a divergence.
            execs, rejected, ntests = self._stats()
            return {
                'verdict': 'crashed',
                'execs': self._afl_execs() or execs,
                'sampled': execs,
                'rejected': rejected,
                'ntests': ntests,
                'diverged_test': 1,
                'counterexample': {
                    'inputs': '',
                    'tape': tape.read_bytes().hex(),
                    'detail': (
                        result.stderr.strip().splitlines()[-1]
                        if result.stderr.strip() else
                        f'harness exited with {result.returncode}'
                    ),
                },
            }

        parsed = self._parse(result.stdout)
        sampled, rejected, ntests = self._stats()

        parsed['execs'] = self._afl_execs() or parsed['execs']
        parsed['sampled'] = sampled
        parsed['rejected'] = rejected
        parsed['ntests'] = max(parsed['ntests'], ntests)

        if parsed['counterexample'] is not None:
            parsed['counterexample']['tape'] = tape.read_bytes().hex()

        return parsed

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def _parse(self, stdout: str) -> dict:
        match = RESULT_RE.search(stdout)
        if not match:
            raise RunError(f"Could not parse harness output:\n{stdout}")

        g = match.groupdict()
        verdict = g['verdict']

        counterexample = None
        if verdict == 'diverged':
            counterexample = {
                'inputs': (g['inputs'] or '').strip(),
                'tape': '',
                'detail': (g['report'] or '').strip(),
            }

        return {
            'verdict': verdict,
            'execs': int(g['execs']),
            'sampled': int(g['execs']),
            'rejected': int(g['rejected']),
            'ntests': int(g['ntests']),
            'diverged_test': int(g['test']) if g['test'] else None,
            'counterexample': counterexample,
        }

    def _write_results(self, parsed: dict) -> Path:
        """Emit a result JSON alongside the symbolic engine's.

        The `fuzz` key nests under the same per-test keys the symbolic engine
        uses, so a `both` run can merge the two without either clobbering the
        other.
        """
        ntests = max(parsed['ntests'], 1)
        diverged = parsed['diverged_test']

        # The rejection counts are sampled from one forked process, so express
        # them as a rate rather than pretending to an exact total.
        sampled = parsed.get('sampled') or 0
        rate = (parsed['rejected'] / sampled) if sampled else 0.0

        results = {}
        for i in range(1, ntests + 1):
            is_diverged = diverged == i

            if is_diverged:
                verdict = (
                    'crashed' if parsed['verdict'] == 'crashed' else 'diverged'
                )
            elif parsed['verdict'] == 'starved':
                verdict = 'starved'
            else:
                verdict = 'passed'

            results[f'{self.testfile.stem}.test_{i}'] = {
                'fuzz': {
                    'verdict': verdict,
                    'execs': parsed['execs'],
                    # Fraction of inputs turned away by assume()/_assert()
                    # before reaching the comparison. A pass at a rate of 1.0
                    # establishes nothing.
                    'rejection_rate': round(rate, 4),
                    'sampled_execs': sampled,
                    'sampled_rejected': parsed['rejected'],
                    'counterexample': (
                        parsed['counterexample'] if is_diverged else None
                    ),
                }
            }

        self.results_dir.mkdir(parents=True, exist_ok=True)
        out = self.results_dir / f'{self.binary.name}_result.json'
        out.write_text(json.dumps(results, indent=2))

        logger.info("Fuzz results written to %s", out)
        return out

    def run(self) -> Path:
        self.compile()
        parsed = self._run_afl()

        if parsed['verdict'] in ('diverged', 'crashed'):
            ce = parsed['counterexample']
            logger.warning(
                "Summary %s after %d execs\n  inputs: %s\n  %s",
                parsed['verdict'], parsed['execs'],
                ce['inputs'] or '(not decoded)', ce['detail'],
            )
        elif parsed['verdict'] == 'starved':
            logger.warning(
                "All %d sampled inputs were rejected by assume()/_assert(): "
                "the summary was never actually compared against the concrete "
                "function. Widen the input bounds or seed the corpus.",
                parsed['sampled'],
            )
        else:
            sampled = parsed.get('sampled') or 0
            rate = (parsed['rejected'] / sampled) if sampled else 0.0
            logger.info(
                "No divergence in %d execs (%.0f%% of sampled inputs "
                "rejected)", parsed['execs'], rate * 100,
            )

        return self._write_results(parsed)
