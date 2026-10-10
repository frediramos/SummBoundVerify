"""
Step 2: Claude gets the summaries the fuzzer accepted, and the testsuite's
failures, until the testsuite passes with them, or the attempts run out.
Every summary Claude changes is fuzzed again, and must still pass. The
final summaries are copied back to summaries/obtained/. Everything is
saved to results/<run id>/step2/.
"""

import os
import uuid
import shutil
import subprocess

from pathlib import Path
from dataclasses import dataclass

from .common import (
    REPO,
    PROMPTS,
    OBTAINED,
    SUITE_TIMEOUT,
    Run,
    Check,
    Target,
    now,
    sha256,
    render,
    new_work,
    run_fuzzer,
    write_json,
    code_block,
    run_command,
    sum_metrics,
    claude_metrics,
    save_transcript,
    copy_fuzzer_setup,
    what_fuzzer_found,
)


TESTSUITE = Path("tests/files/testsuite")
TESTS = TESTSUITE / "klee-testsuite"

# Where make run logs each test, under its LOG= folder
RUN_KIND = Path("ours-summaries/sym-fname-1")


@dataclass
class TestRun:
    """One run of the testsuite: each test's verdict."""

    verdicts: dict[str, bool]   # e.g. {"read/test_01": True}
    time_s: float
    failures: str               # the failed tests, as report.py explains them

    @property
    def passed(self) -> int:
        return sum(self.verdicts.values())

    @property
    def all_passed(self) -> bool:
        return self.passed == len(self.verdicts)

    def suites(self) -> dict[str, list[int]]:
        """Each suite's [tests passed, tests]."""
        counts = {}
        for test, passed in sorted(self.verdicts.items()):
            suite = counts.setdefault(test.split("/")[0], [0, 0])
            suite[0] += passed
            suite[1] += 1
        return counts

    def record(self) -> dict:
        return {
            "passed": self.passed,
            "tests": len(self.verdicts),
            "suites": self.suites(),
            "failed": sorted(t for t, ok in self.verdicts.items() if not ok),
            "time_s": self.time_s,
        }


@dataclass
class Attempt:
    """
    One `claude -p` call, the fuzzer's checks of the summaries it changed,
    and the testsuite's run on all of them.
    """

    number: int
    claude: dict                # time, tokens and cost of the call
    changed: list[str]          # the functions whose summary changed
    fuzz: dict[str, Check]      # the fuzzer's check of each changed one
    tests: TestRun

    @property
    def passed(self) -> bool:
        fuzz_passed = all(c.passed for c in self.fuzz.values())
        return fuzz_passed and self.tests.all_passed

    def record(self) -> dict:
        """iter-<number>.json"""
        return {
            "iteration": self.number,
            "claude": self.claude,
            "changed": self.changed,
            "fuzzer": {fn: c.record() for fn, c in self.fuzz.items()},
            "testsuite": self.tests.record(),
            "passed": self.passed,
        }


# -- Working copy ------------------------------------------------------------

def make_work(targets: list[Target], commit: str | None) -> Path:
    """
    Claude's working copy: the repository without the existing summaries,
    plus the summaries the fuzzer accepted, their manual pages, and the
    testsuite's tests to read.
    """
    work = new_work("testsuite", targets, commit)

    for target in targets:
        shutil.copytree(REPO / target.summary_dir, work / target.summary_dir)

        (work / target.manual_copy).parent.mkdir(parents=True)
        shutil.copy(target.manual, work / target.manual_copy)

    # The tests are in a submodule, which the copy of the repository lacks
    for folder in ("include", "individual-tests"):
        shutil.copytree(
            REPO / TESTS / folder,
            work / TESTS / folder,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("klee-out-*", "klee-last", "*.bc")
        )

    return work


def snapshot(targets: list[Target], work: Path) -> dict[str, str]:
    """Each summary's hash, to tell which ones an attempt changed."""
    return {t.function: sha256(work / t.summary) for t in targets}


def save_summaries(targets: list[Target], work: Path, folder: Path):
    """Copies the summaries as they are now, e.g. to summaries-<n>/."""
    folder.mkdir(parents=True)
    for target in targets:
        shutil.copy(work / target.summary, folder / target.output)


def contents(targets: list[Target], work: Path) -> dict[str, bytes]:
    """Each summary as it is now in the working copy."""
    return {t.function: (work / t.summary).read_bytes() for t in targets}


def publish(targets: list[Target], good: dict[str, bytes]):
    """
    Copies each summary's latest version the fuzzer accepted back to
    summaries/obtained/.
    """
    for target in targets:
        (REPO / target.summary).write_bytes(good[target.function])


# -- The testsuite -----------------------------------------------------------

def run_testsuite(run: Run, work: Path, out: Path, name: str) -> TestRun:
    """
    Runs every test, with the summaries in the working copy linked in, and
    saves the logs in <name>/ and make's output as <name>.log.
    """
    logs = out / name
    command = (
        f"make -s run -j{run.jobs} FS=ours "
        f"SUMMARIES={work / OBTAINED} LOG={logs}"
    )
    env = dict(os.environ, PYTHONPATH=str(work / "src"))

    _, elapsed, log = run_command(
        command,
        REPO / TESTSUITE,
        env,
        timeout=SUITE_TIMEOUT
    )
    (out / f"{name}.log").write_text(log)

    verdicts = {}
    for f in sorted((logs / RUN_KIND).glob("*/test_*.log")):
        test = f"{f.parent.name}/{f.stem}"
        lines = f.read_text().splitlines()
        verdicts[test] = bool(lines) and lines[-1] == "== PASSED"

    failures = subprocess.run(
        ["python3", "report.py", str(logs / RUN_KIND), "--failed"],
        cwd=REPO / TESTSUITE,
        capture_output=True,
        text=True
    ).stdout

    # Its first line names the log folder, a path outside the working copy
    failures = failures.split("\n", 1)[-1]

    return TestRun(verdicts, elapsed, failures)


# -- Prompt and feedback -----------------------------------------------------

def what_failed(
    targets: list[Target],
    tests: TestRun,
    fuzz: dict[str, Check]
) -> str:
    """The {{report}}: the fuzzer's findings, then the failed tests."""
    parts = []

    for target in targets:
        check = fuzz.get(target.function)
        if check is not None and not check.passed:
            parts.append(
                f"The fuzzer rejected `{target.summary}`.\n\n"
                + what_fuzzer_found(check)
            )

    if not tests.all_passed:
        failed = len(tests.verdicts) - tests.passed
        parts.append(
            f"{failed} of {len(tests.verdicts)} tests failed:\n\n"
            + code_block(tests.failures.strip())
        )

    return "\n\n".join(parts)


def first_prompt(targets: list[Target], start: TestRun) -> str:
    """testsuite_prompt.md, filled in with the first run's failures."""
    manuals = "\n".join(
        f"- `{t.function}`: `{t.manual_copy}`" for t in targets
    )
    return render(PROMPTS / "testsuite_prompt.md", {
        "manuals": manuals,
        "summaries": OBTAINED,
        "tests": TESTS / "individual-tests",
        "helpers": TESTS / "include",
        "report": what_failed(targets, start, {}),
    })


def feedback(targets: list[Target], attempt: Attempt, out: Path) -> str:
    """
    testsuite_feedback.md, filled in with what failed; saved as
    feedback-<n>.txt.
    """
    message = render(PROMPTS / "testsuite_feedback.md", {
        "summaries": OBTAINED,
        "report": what_failed(targets, attempt.tests, attempt.fuzz),
    })
    (out / f"feedback-{attempt.number}.txt").write_text(message)
    return message


# -- The loop ----------------------------------------------------------------

def attempt(
    run: Run,
    targets: list[Target],
    session: str,
    work: Path,
    out: Path,
    number: int,
    message: str
) -> Attempt:
    """
    Sends `message` to Claude, fuzzes each summary it changed, then runs
    the testsuite. Saves claude-<n>.json, summaries-<n>/,
    fuzz-<n>-<function>.*, testsuite-<n>/ and iter-<n>.json.
    """
    before = snapshot(targets, work)
    result, wall = run.claude.ask(message, session, number == 1, work)
    write_json(out / f"claude-{number}.json", result)

    after = snapshot(targets, work)
    changed = [t for t in targets if after[t.function] != before[t.function]]
    save_summaries(targets, work, out / f"summaries-{number}")

    fuzz = {}
    for target in changed:
        # The fuzzer's setup as the target defines it, whatever Claude did
        copy_fuzzer_setup(target, work / target.summary_dir)
        name = f"fuzz-{number}-{target.function}"
        fuzz[target.function] = run_fuzzer(target, work, out, name)

    tests = run_testsuite(run, work, out, f"testsuite-{number}")

    done = Attempt(
        number,
        claude_metrics(result, wall),
        [t.function for t in changed],
        fuzz,
        tests
    )
    write_json(out / f"iter-{number}.json", done.record())
    return done


def write_summary(start: TestRun, attempts: list[Attempt], out: Path):
    """summary.json: the testsuite before and after, and the metrics."""
    end = attempts[-1].tests if attempts else start
    passed = attempts[-1].passed if attempts else start.all_passed

    write_json(out / "summary.json", {
        "passed": passed,
        "iterations": len(attempts),
        "start": start.record(),
        "end": end.record(),
        "totals": {
            **sum_metrics([a.claude for a in attempts]),
            "fuzzer_time_s": sum(
                c.time_s for a in attempts for c in a.fuzz.values()
            ),
            "testsuite_time_s": start.time_s + sum(
                a.tests.time_s for a in attempts
            ),
        },
        "finished_at": now(),
    })


def print_tests(
    label: str,
    tests: TestRun,
    changed: list[str] | None = None
):
    total = len(tests.verdicts)
    edits = f"   changed {', '.join(changed)}" if changed else ""
    print(f"    {label:<10} {tests.passed:>3}/{total} tests pass{edits}")


def fix(run: Run, targets: list[Target]) -> bool:
    """
    Step 2 for all the targets, whose summaries the fuzzer accepted.
    Returns whether every test and every fuzzer check passes in the end.
    """
    out = run.out / "step2"
    out.mkdir(parents=True)
    session = str(uuid.uuid4())
    work = make_work(targets, run.commit)

    save_summaries(targets, work, out / "summaries-0")
    good = contents(targets, work)
    start = run_testsuite(run, work, out, "testsuite-0")
    write_json(out / "start.json", start.record())
    print_tests("start", start)

    attempts = []
    if not start.all_passed:
        message = first_prompt(targets, start)
        (out / "prompt.txt").write_text(message)

        for number in range(1, run.max_iters + 1):
            attempts.append(
                attempt(run, targets, session, work, out, number, message)
            )
            print_tests(
                f"attempt {number}",
                attempts[-1].tests,
                attempts[-1].changed
            )

            current = contents(targets, work)
            for fn, check in attempts[-1].fuzz.items():
                if check.passed:
                    good[fn] = current[fn]

            if attempts[-1].passed:
                break
            message = feedback(targets, attempts[-1], out)

        save_transcript(session, out)

    write_summary(start, attempts, out)
    publish(targets, good)

    if run.keep_work:
        print(f"    working copy kept in {work}")
    else:
        shutil.rmtree(work)

    return attempts[-1].passed if attempts else start.all_passed
