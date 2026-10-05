#!/usr/bin/env python3
"""Explain the results of a logged test run: test by test, then grouped by reason.

make run saves each test's log to logs/<fs>/sym-fname-<N>/<suite>/test_NN.log: summbv's
output, ending in the "== PASSED" or "== FAILED" line the Makefile appends.

examples:
  make run FS=angr
  ./report.py                            every run in logs/
  ./report.py logs/angr/sym-fname-1                  one run: every test, then the failures by reason
  ./report.py logs/angr/sym-fname-1 --failed         failed tests only
  ./report.py logs/angr/sym-fname-1 --suite open     one suite
  ./report.py logs/angr/sym-fname-1 --summary        only the totals and the reasons
"""

import os
import re
import sys
import signal
import argparse

from pathlib import Path
from collections import Counter
from dataclasses import dataclass

HERE = Path(__file__).resolve().parent
TESTS_DIR = HERE / "klee-testsuite" / "individual-tests"
LOGS_DIR = HERE / "logs"

PASSED, FAILED, UNKNOWN = "PASSED", "FAILED", "UNKNOWN"
VERDICT_LINES = {
    "== PASSED": PASSED,
    "== FAILED": FAILED
}

# The exception summbv ends with, e.g.
# summboundverify.exceptions.exceptions.UnsatConstraintError: Unsatisfiable ...
ERROR_LINE = re.compile(r"^(?:[\w.]+\.)?(\w+(?:Error|Exception)): (.*)$")

# angr spells out sign extension bit by bit: x sign-extended is
# (x[31:31] .. x[31:31] .. ... .. x), and a slice x[23:16] sign-extended is
# (x[23:23] .. ... .. x[23:16])
SIGN_EXTENSION = re.compile(
    r"\(([^\s()\[\]]+)\[(\d+):\2\](?: \.\. \1\[\2:\2\])* \.\. \1(\[\2:\d+\])?\)"
)


# Results
# ---------------------------------------------------------------------------

@dataclass
class Result:
    suite: str        # open, close, ...
    name: str         # test_01, ...
    verdict: str      # PASSED, FAILED or UNKNOWN
    reason: str       # why it failed, in words; empty if it passed

    @property
    def passed(self) -> bool:
        return self.verdict == PASSED


def read_result(log: Path) -> Result:
    lines = log.read_text(errors="replace").splitlines()
    verdicts = [VERDICT_LINES[line] for line in lines if line in VERDICT_LINES]
    output = [line for line in lines if line not in VERDICT_LINES]

    # Logs from before the Makefile recorded verdicts have none: a test
    # failed if summbv ended with an error, and is unknown otherwise
    if verdicts:
        verdict = verdicts[-1]
    elif last_error(output):
        verdict = FAILED
    else:
        verdict = UNKNOWN

    if verdict == PASSED:
        reason = ""
    elif verdict == UNKNOWN:
        reason = "the log records no verdict and no error"
    else:
        reason = explain(output)
    return Result(log.parent.name, log.stem, verdict, reason)


def read_results(logs: Path, suites: list[str]) -> list[Result]:
    results = [read_result(log) for log in sorted(logs.glob("*/*.log"))]
    if suites:
        results = [r for r in results if r.suite in suites]
    return results


# Explaining failures
# ---------------------------------------------------------------------------

def last_error(output: list[str]) -> tuple[str, str] | None:
    """The (exception, message) summbv ended with, if any."""
    for line in reversed(output):
        m = ERROR_LINE.match(line.strip())
        if m:
            return m.group(1), m.group(2)
    return None


def readable(constraint: str) -> str:
    """`constraint` as angr prints it, made shorter to read."""
    constraint = SIGN_EXTENSION.sub(r"SignExt(\1\3)", constraint)
    m = re.fullmatch(r"<Bool (.*)>", constraint)
    return m.group(1) if m else constraint


def explain(output: list[str]) -> str:
    """Why a test failed, in words, from summbv's output."""
    error = last_error(output)

    if error is None:
        if not any(line.strip() for line in output):
            return "no output: did the test compile?"
        return "the test failed without an error message"

    kind, message = error

    # Native runs (FS=native) number the failing __assume or __sra_assert
    if kind == "PreconditionError":
        return f"precondition failed: {message}"

    if kind == "AssertionError":
        return f"assertion failed: {message}"

    if kind == "UnsatConstraintError":
        return "precondition failed: an __assume can never hold"

    if kind == "AssertConstraintError":
        m = re.search(r"does not imply: '(.*)'\.?$", message)
        constraint = readable(m.group(1)) if m else message
        return f"assertion failed: {constraint}"

    if kind == "NotImplementedApiError":
        return f"not implemented: {message}"

    if kind == "TimeoutError":
        return f"timed out: {message}"

    return f"{kind}: {message}"


def reason_group(reason: str) -> str:
    """`reason` without the details that differ between equal failures:
    variable numbering (_4_32) and hex values."""
    reason = re.sub(r"0x[0-9a-f]+", "N", reason)
    return re.sub(r"(_\d+)+\b", "_", reason)


def description(result: Result) -> str:
    """The test's one-line description, from its header comment:
     * test_01.c - O_RDONLY on existing file succeeds
    """
    source = TESTS_DIR / result.suite / f"{result.name}.c"
    if not source.exists():
        return ""

    for line in source.read_text(errors="replace").splitlines():
        m = re.match(rf"^\s*\*\s*{result.name}\.c\s*-\s*(.*)$", line)
        if m:
            return m.group(1).strip()

    return ""


# Printing
# ---------------------------------------------------------------------------

def totals(results: list[Result]) -> str:
    """e.g. "133 tests: 17 passed, 116 failed"."""
    verdicts = Counter(r.verdict for r in results)
    parts = [
        f"{verdicts[v]} {v.lower()}"
        for v in (PASSED, FAILED, UNKNOWN) if verdicts[v]
    ]
    return f"{len(results)} tests: " + ", ".join(parts)


def print_tests(results: list[Result], failed_only: bool):
    """Each suite, then each of its tests: verdict, name, description, and
    on the next line why it failed."""
    name_width = max(len(r.name) for r in results)
    verdict_width = len(UNKNOWN)
    indent = " " * (2 + verdict_width + 2 + name_width + 2)

    for suite in sorted({r.suite for r in results}):
        tests = [r for r in results if r.suite == suite]
        shown = [r for r in tests if not (failed_only and r.passed)]
        if not shown:
            continue

        passed = sum(r.passed for r in tests)
        print(f"{suite}  {passed}/{len(tests)} passed")

        for r in shown:
            print(
                f"  {r.verdict:<{verdict_width}}  {r.name:<{name_width}}  {description(r)}")
            if r.reason:
                print(f"{indent}{r.reason}")

        print()


def print_reasons(results: list[Result]):
    """How many tests failed for each reason, most common first."""
    reasons = Counter(reason_group(r.reason) for r in results if not r.passed)
    if not reasons:
        return

    print("Failures by reason")
    for reason, n in reasons.most_common():
        print(f"  {n:>4}  {reason}")
    print()


def report(logs: Path, args: argparse.Namespace) -> bool:
    """Print the report for one log directory. False if it has no logs."""
    results = read_results(logs, args.suite)

    if not results:
        where = f"{logs}/<suite>/*.log"
        if args.suite:
            where += f" for suite {', '.join(args.suite)}"
        print(f"report.py: no logs in {where}", file=sys.stderr)
        return False

    print(f"{logs}  {totals(results)}")
    print()

    if not args.summary:
        print_tests(results, args.failed)

    print_reasons(results)
    return True


# Command line
# ---------------------------------------------------------------------------

def find_runs(logs: Path) -> list[Path]:
    """The run directories under `logs`: those holding <suite>/test_NN.log,
    e.g. logs/angr/sym-fname-1 and logs/angr/sym-fname-3."""
    runs = {log.parent.parent for log in logs.rglob("*/test_*.log")}
    return sorted(Path(os.path.relpath(run)) for run in runs)


def parse_args() -> argparse.Namespace:
    summary, details = __doc__.split("\n\n", 1)

    parser = argparse.ArgumentParser(
        description=summary,
        epilog=details,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "logs", type=Path, nargs="*",
        help="log directory of one run, e.g. logs/angr/sym-fname-1 (default: every run in logs/)",
    )
    parser.add_argument(
        "-f", "--failed", action="store_true",
        help="list failed tests only",
    )
    parser.add_argument(
        "-s", "--suite", action="append", default=[], metavar="SUITE",
        help="report only this suite (open, close, ...); can be repeated",
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="print only the totals and the failures by reason",
    )
    return parser.parse_args()


def main() -> int:
    # Exit quietly when piped into a command like 'less'
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    args = parse_args()

    if not args.logs:
        args.logs = find_runs(LOGS_DIR)
        if not args.logs:
            print(f"report.py: no logs in {LOGS_DIR}: run make run first", file=sys.stderr)
            return 1

    for logs in args.logs:
        status = report(logs, args)
        if not status:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
