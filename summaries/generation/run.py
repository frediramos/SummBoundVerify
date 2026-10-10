#!/usr/bin/env python3
"""
Runs a summary generation: Claude writes the summaries of libc functions,
until the fuzzer accepts each one (step 1), then fixes them until the
testsuite passes with all of them (step 2).

    ./run.py [function ...] [--model M] [--effort E] [--max-iters N]
             [--commit C] [--jobs N] [-keep-work]
    ./run.py report [run] [--table T] [-csv]

Without functions, every target in targets/ is generated, then step 2 runs
if the fuzzer accepted every summary. With functions, only step 1 runs:
the testsuite needs all the summaries. Everything is saved to
results/<run id>/; `report` prints a run's tables. See README.md.

Run it from summbv's virtualenv.
"""

import io
import os
import sys
import shutil
import argparse

from datetime import datetime, timezone

from lib import report
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
    git,
    fail,
    now,
    sha256,
    write_json,
    uncommitted_sha256,
)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
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
    return ap.parse_args()


def write_meta(run: Run, targets: list[Target]):
    """meta.json: everything that defines the run, so runs can be compared."""
    prompts = sorted(PROMPTS.glob("*.md"))
    context = sorted(p for p in (HERE / "context").rglob("*") if p.is_file())
    inputs = [*prompts, *context, *(f for t in targets for f in t.files())]

    commit = git("rev-parse", run.commit or "HEAD").decode().strip()
    uncommitted = None if run.commit else uncommitted_sha256()
    generation_dirty = git("status", "--porcelain", "--", str(HERE)).strip()

    write_json(run.out / "meta.json", {
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
    })


def start_run(args: argparse.Namespace) -> tuple[Run, list[Target]]:
    """Checks the targets, then creates the results folder and meta.json."""
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

    run.out.mkdir(parents=True)
    write_meta(run, targets)
    return run, targets


def write_summary(run: Run, step1: dict[str, bool], step2: bool | None):
    """summary.json: each step's outcome. The metrics are in each step's."""
    write_json(run.out / "summary.json", {
        "run_id": run.run_id,
        "step1": step1,
        "step2": step2,
        "passed": bool(step2),
        "finished_at": now(),
    })


def generate() -> int:
    # Show progress line by line, also when the output goes to a file
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(line_buffering=True)

    run, targets = start_run(parse_args())
    source = run.commit or "working tree"
    print(
        f"run {run.run_id}  "
        f"({run.claude.model}, effort {run.claude.effort}, {source})"
    )

    print("step 1: fuzzer")
    step1 = {t.function: fuzzing.generate(run, t) for t in targets}

    rejected = [fn for fn, passed in step1.items() if not passed]
    if rejected:
        write_summary(run, step1, None)
        print(f"step 2 skipped: the fuzzer rejected {', '.join(rejected)}")
        return 1

    missing = sorted(set(Target.all()) - set(step1))
    if missing:
        write_summary(run, step1, None)
        print(f"step 2 skipped: no summaries of {', '.join(missing)}")
        return 0

    print("step 2: testsuite")
    step2 = testsuite.fix(run, targets)
    write_summary(run, step1, step2)

    outcome = "passed" if step2 else "did not pass"
    print(f"testsuite {outcome}  ->  {run.out.relative_to(HERE)}")
    return 0 if step2 else 1


def main() -> int:
    if sys.argv[1:2] == ["report"]:
        report.main(sys.argv[2:])
        return 0
    return generate()


if __name__ == "__main__":
    sys.exit(main())
