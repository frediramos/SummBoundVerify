#!/usr/bin/env python3
"""
Runs a summary generation: Claude writes the summaries of libc functions,
until the fuzzer accepts each one (step 1), then fixes them until the
testsuite passes with all of them (step 2).

    ./run.py [function ...] [--model M] [--effort E] [--max-iters N]
             [--commit C] [--jobs N] [-keep-work] [-step2]
    ./run.py report [run ...] [--table T] [-csv]

Without functions, every target in targets/ is generated, then step 2 runs
if the fuzzer accepted every summary. With functions, only step 1 runs:
the testsuite needs all the summaries. With -step2, only step 2 runs, on
the summaries earlier runs' step 1 left in summaries/obtained/. Everything
is saved to results/<run id>/; `report` prints a run's tables. See
README.md.

Run it from summbv's virtualenv.
"""

import io
import os
import sys
import shutil
import argparse

from datetime import datetime, timezone

from lib import report
from lib import sources
from lib import fuzzing
from lib import testsuite

from lib.common import (
    HERE,
    TOOLS,
    PROMPTS,
    ALLOWED,
    DISALLOWED,
    Run,
    Claude,
    Target,
    ClaudeError,
    git,
    fail,
    now,
    sha256,
    write_json,
    uncommitted_sha256,
)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog="To print runs' tables instead: ./run.py report [run ...] "
               "[--table T] [-csv] (see ./run.py report -h)"
    )
    ap.add_argument(
        "functions",
        nargs="*",
        help="folders in targets/ (default: all of them)"
    )
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--effort", default="high")
    ap.add_argument(
        "--max-iters",
        type=int,
        default=10,
        help="attempts before giving up, in each step (default: 10)"
    )
    ap.add_argument(
        "--commit",
        help="repository version Claude works on "
             "(default: the working tree, as it is on disk)"
    )
    ap.add_argument(
        "--jobs",
        type=int,
        default=os.cpu_count(),
        help="testsuite tests run at a time (default: one per CPU)"
    )
    ap.add_argument(
        "-keep-work",
        action="store_true",
        help="keep Claude's working copies, to inspect them"
    )
    ap.add_argument(
        "-step2",
        action="store_true",
        help="run step 2 only, on the summaries in summaries/obtained/, "
             "which earlier runs' step 1 must have accepted"
    )
    return ap.parse_args()


def meta(run: Run, targets: list[Target]) -> dict:
    """meta.json: everything that defines the run, so runs can be compared."""
    prompts = sorted(PROMPTS.glob("*.md"))
    context = sorted(p for p in (HERE / "context").rglob("*") if p.is_file())
    inputs = [*prompts, *context, *(f for t in targets for f in t.files())]

    commit = git("rev-parse", run.commit or "HEAD").decode().strip()
    uncommitted = None if run.commit else uncommitted_sha256()
    generation_dirty = git("status", "--porcelain", "--", str(HERE)).strip()

    return {
        "run_id": run.run_id,
        "functions": [t.function for t in targets],
        "source": "commit" if run.commit else "working tree",
        "commit": commit,
        "uncommitted_sha256": uncommitted,
        "generation_dir_uncommitted_changes": bool(generation_dirty),
        "model": run.claude.model,
        "effort": run.claude.effort,
        "max_iters": run.max_iters,
        "jobs": run.jobs,
        "claude_version": run.claude.version(),
        "tools": TOOLS,
        "allowed": ALLOWED,
        "disallowed": DISALLOWED,
        "inputs_sha256": {
            str(p.relative_to(HERE)): sha256(p) for p in inputs
        },
        "started_at": now(),
    }


def start_run(args: argparse.Namespace) -> tuple[Run, list[Target]]:
    """
    Checks the targets, and with -step2 where their summaries come from,
    then creates the results folder and meta.json.
    """
    if args.step2 and args.functions:
        fail("-step2 runs on every target: give no functions")

    functions = args.functions or Target.all()
    targets = [Target.load(fn) for fn in functions]

    if not shutil.which("summbv"):
        fail("summbv not on PATH; activate its virtualenv")

    # When the run started, in UTC, e.g. 2026-10-12_09-15-00: readable, and
    # sorted by time, so that the latest run is the last one
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    run = Run(
        claude=Claude.find(args.model, args.effort),
        run_id=run_id,
        out=HERE / "results" / run_id,
        commit=args.commit,
        max_iters=args.max_iters,
        jobs=args.jobs,
        keep_work=args.keep_work
    )

    record = meta(run, targets)
    if args.step2:
        record["step1_sources"] = sources.find(targets, record)

    run.out.mkdir(parents=True)
    write_json(run.out / "meta.json", record)
    return run, targets


def write_summary(
    run: Run,
    step1: dict[str, bool],
    step2: bool | None,
    error: str | None = None
):
    """
    summary.json: each step's outcome, and the error that stopped the run,
    if any. The metrics are in each step's.
    """
    write_json(run.out / "summary.json", {
        "run_id": run.run_id,
        "step1": step1,
        "step2": step2,
        "passed": bool(step2),
        "error": error,
        "finished_at": now(),
    })


def run_steps(
    run: Run,
    targets: list[Target],
    step1: dict[str, bool]
) -> bool | None:
    """
    Step 1 for each target, recording its outcome in `step1`, then step 2
    if every target passed it. Returns step 2's outcome, or None if it did
    not run.
    """
    print("step 1: fuzzer")
    for target in targets:
        step1[target.function] = fuzzing.generate(run, target)

    rejected = [fn for fn, passed in step1.items() if not passed]
    if rejected:
        print(f"step 2 skipped: the fuzzer rejected {', '.join(rejected)}")
        return None

    missing = sorted(set(Target.all()) - set(step1))
    if missing:
        print(f"step 2 skipped: no summaries of {', '.join(missing)}")
        return None

    print("step 2: testsuite")
    return testsuite.fix(run, targets)


def step2_only(
    run: Run,
    targets: list[Target],
    step1: dict[str, bool]
) -> bool:
    """
    Step 2, on the summaries earlier runs' step 1 accepted, as meta.json
    records them.
    """
    found = sources.read(run.out / "meta.json")["step1_sources"]
    print("step 1: from earlier runs")
    for target in targets:
        source = found[target.function]
        print(
            f"  {target.function:<10} run {source['run']}, "
            f"attempt {source['attempt']}"
        )
        step1[target.function] = True

    print("step 2: testsuite")
    return testsuite.fix(run, targets)


def generate() -> int:
    # Show progress line by line, also when the output goes to a file
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(line_buffering=True)

    args = parse_args()
    run, targets = start_run(args)

    source = run.commit or "working tree"
    print(
        f"run {run.run_id}  "
        f"({run.claude.model}, effort {run.claude.effort}, {source})"
    )

    # A call to Claude that fails outright (e.g. no credit left) stops the
    # run: it is not an attempt
    step1: dict[str, bool] = {}
    try:
        if args.step2:
            step2 = step2_only(run, targets, step1)
        else:
            step2 = run_steps(run, targets, step1)
    except ClaudeError as e:
        write_summary(run, step1, None, error=str(e))
        print(f"run stopped, a call to claude failed: {e}")
        return 1

    write_summary(run, step1, step2)

    if step2 is None:
        return 0 if all(step1.values()) else 1

    outcome = "passed" if step2 else "did not pass"
    print(f"testsuite {outcome}  ->  {run.out.relative_to(HERE)}")
    return 0 if step2 else 1


def main() -> int:
    if sys.argv[1:2] == ["report"]:
        report.main(sys.argv[2:], prog="run.py report")
        return 0
    return generate()


if __name__ == "__main__":
    sys.exit(main())
