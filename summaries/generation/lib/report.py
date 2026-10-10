"""
Tables of a generation run in results/, for the paper.

    ./run.py report                     the latest run: its three tables
    ./run.py report 20261012T091500Z    a given run
    ./run.py report --table step2       one table: step1, step2 or summary
    ./run.py report -csv                raw values as CSV, e.g. for plots

The tables:
    step1    one row per function: the attempts until the fuzzer accepted
             its summary, and their cost
    step2    one row per testsuite run: tests passed, overall and per suite,
             the summaries the attempt before it changed, and its cost
    summary  one row per function: its fuzzer runs (step 1, then each change
             in step 2) and its testsuite runs until its suite passed (-:
             never), with step 1's cost; then step 2's cost, and the total

Columns:
    model time  the model's time (duration_api_ms)
    wall time   the claude calls' time, tools included; checks excluded
    input       input tokens: uncached + written to cache + read from cache
    output      output tokens
"""

import sys
import csv
import json
import signal
import argparse

from typing import Callable

from pathlib import Path
from tabulate import tabulate
from dataclasses import dataclass

signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# The generation folder
HERE = Path(__file__).resolve().parents[1]
RESULTS = HERE / "results"

TABLES = ("step1", "step2", "summary")


# -- Formatting --------------------------------------------------------------

def duration(seconds: float) -> str:
    seconds = round(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def tokens(n: float) -> str:
    if n < 1_000:
        return f"{n:.0f}"
    if n < 1_000_000:
        return f"{n / 1_000:.1f}k"
    return f"{n / 1_000_000:.2f}M"


def dollars(x: float) -> str:
    return f"${x:.2f}"


def out_of(total: int) -> Callable:
    """Formats a count as count/total."""
    return lambda n: f"{n}/{total}"


@dataclass
class Column:
    key: str
    header: str
    fmt: Callable = str
    numeric: bool = True        # right-aligned

    def cell(self, value) -> str:
        if value is None or value == "":
            return "-"
        return self.fmt(value) if self.numeric else str(value)


# The cost of Claude's calls, in every table
COST = [
    Column("api_s", "model time", duration),
    Column("wall_s", "wall time", duration),
    Column("input_tokens", "input", tokens),
    Column("output_tokens", "output", tokens),
    Column("cost_usd", "cost", dollars),
]


def cost(claude: dict) -> dict:
    """A row's cost columns, from a call's metrics or summed ones."""
    return {
        "api_s": (claude["duration_api_ms"] or 0) / 1000,
        "wall_s": claude["wall_s"],
        "input_tokens": (
            claude["input_tokens"]
            + claude["cache_creation_input_tokens"]
            + claude["cache_read_input_tokens"]
        ),
        "output_tokens": claude["output_tokens"],
        "cost_usd": claude["cost_usd"] or 0,
    }


def add_costs(rows: list[dict]) -> dict:
    return {
        col.key: sum(r.get(col.key) or 0 for r in rows)
        for col in COST
    }


@dataclass
class Table:
    title: str
    columns: list[Column]
    rows: list[dict]
    total: dict | None = None   # printed after a rule

    def print(self):
        print(self.title)
        print()
        rows = self.rows + ([self.total] if self.total else [])
        cells = [[c.cell(r.get(c.key)) for c in self.columns] for r in rows]
        text = tabulate(
            cells,
            headers=[c.header for c in self.columns],
            colalign=[
                "right" if c.numeric else "left" for c in self.columns
            ],
            disable_numparse=True
        )

        lines = text.splitlines()
        if self.total:
            # The rule under the headers, again above the total
            lines.insert(len(lines) - 1, lines[1])
        print("\n".join(lines))
        print()

    def print_csv(self):
        writer = csv.DictWriter(
            sys.stdout,
            [c.key for c in self.columns],
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(self.rows)


# -- A run's results ---------------------------------------------------------

def read(path: Path) -> dict:
    return json.loads(path.read_text())


def iterations(folder: Path) -> list[dict]:
    """A step's iter-<n>.json files, in order."""
    files = sorted(
        folder.glob("iter-*.json"),
        key=lambda p: int(p.stem.split("-")[1])
    )
    return [read(f) for f in files]


@dataclass
class Results:
    folder: Path
    meta: dict
    step1: dict[str, dict]          # each function's summary.json
    step1_iters: dict[str, list]    # each function's iter-<n>.json
    step2: dict | None              # step 2's summary.json
    step2_runs: list[dict]          # testsuite records: start, then each
    step2_iters: list[dict]

    @classmethod
    def load(cls, folder: Path) -> "Results":
        meta = read(folder / "meta.json")
        functions = meta["functions"]
        step1 = {}
        step1_iters = {}
        for fn in functions:
            summary = folder / "step1" / fn / "summary.json"
            if summary.exists():
                step1[fn] = read(summary)
                step1_iters[fn] = iterations(folder / "step1" / fn)

        step2 = None
        step2_runs = []
        step2_iters = []
        if (folder / "step2" / "summary.json").exists():
            step2 = read(folder / "step2" / "summary.json")
            step2_iters = iterations(folder / "step2")
            step2_runs = [
                read(folder / "step2" / "start.json"),
                *(it["testsuite"] for it in step2_iters),
            ]

        return cls(
            folder,
            meta,
            step1,
            step1_iters,
            step2,
            step2_runs,
            step2_iters
        )


# -- The tables --------------------------------------------------------------

def step1_table(r: Results) -> Table:
    rows = [
        {
            "target": fn,
            "passed": "yes" if s["passed"] else "no",
            "attempts": s["iterations"],
            **cost(s["totals"]),
        }
        for fn, s in r.step1.items()
    ]
    accepted = sum(s["passed"] for s in r.step1.values())

    total = {
        "target": "total",
        "passed": f"{accepted}/{len(r.step1)}",
        "attempts": sum(row["attempts"] for row in rows),
        **add_costs(rows),
    }
    columns = [
        Column("target", "target", numeric=False),
        Column("passed", "passed", numeric=False),
        Column("attempts", "attempts"),
        *COST,
    ]
    return Table("Step 1: fuzzer, one row per target", columns, rows, total)


def step2_table(r: Results) -> Table:
    start = r.step2_runs[0]
    suites = list(start["suites"])

    rows = []
    for number, run in enumerate(r.step2_runs):
        row = {
            "attempt": "start" if number == 0 else number,
            "tests": run["passed"],
            **{f"suite_{s}": run["suites"][s][0] for s in suites},
        }
        if number > 0:
            it = r.step2_iters[number - 1]
            row["changed"] = ", ".join(it["changed"])
            row.update(cost(it["claude"]))
        rows.append(row)

    end = r.step2_runs[-1]
    total = {
        "attempt": "total",
        "tests": end["passed"],
        **{f"suite_{s}": end["suites"][s][0] for s in suites},
        **add_costs(rows),
    }
    columns = [
        Column("attempt", "attempt", numeric=False),
        Column("tests", "tests", out_of(start["tests"])),
        *(
            Column(f"suite_{s}", s, out_of(start["suites"][s][1]))
            for s in suites
        ),
        Column("changed", "changed", numeric=False),
        *COST,
    ]
    return Table("Step 2: testsuite, one row per run", columns, rows, total)


def testsuite_runs(r: Results, function: str) -> int | None:
    """
    The testsuite runs until the function's suite, named after it, passed,
    or None.
    """
    for number, run in enumerate(r.step2_runs):
        passed, tests = run["suites"].get(function, [0, None])
        if passed == tests:
            return number + 1
    return None


def summary_table(r: Results) -> Table:
    rows = []
    for fn, s in r.step1.items():
        refuzzed = sum(fn in it["fuzzer"] for it in r.step2_iters)
        rows.append({
            "target": fn,
            "fuzzer_runs": s["iterations"] + refuzzed,
            "testsuite_runs": testsuite_runs(r, fn) if r.step2 else None,
            **cost(s["totals"]),
        })

    runs = len(r.step2_runs) or None
    if r.step2:
        rows.append({
            "target": "testsuite",
            "testsuite_runs": runs,
            **cost(r.step2["totals"]),
        })

    total = {
        "target": "total",
        "fuzzer_runs": sum(row.get("fuzzer_runs") or 0 for row in rows),
        "testsuite_runs": runs,
        **add_costs(rows),
    }
    columns = [
        Column("target", "target", numeric=False),
        Column("fuzzer_runs", "fuzzer runs"),
        Column("testsuite_runs", "testsuite runs"),
        *COST,
    ]
    return Table("Summary", columns, rows, total)


# -- Main --------------------------------------------------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        prog="run.py report",
        description=__doc__.split("\n\n")[0]
    )
    ap.add_argument(
        "run",
        nargs="?",
        help="a run id in results/ (default: the latest)"
    )
    ap.add_argument(
        "--table",
        choices=TABLES,
        help="print only this table (default: all three)"
    )
    ap.add_argument(
        "-csv",
        action="store_true",
        help="print raw values as CSV"
    )
    return ap.parse_args(argv)


def find_run(run: str | None) -> Path:
    runs = sorted(p for p in RESULTS.glob("*") if (p / "meta.json").exists())
    if not runs:
        sys.exit("run.py report: no runs in results/")
    if run is None:
        return runs[-1]
    if not (RESULTS / run / "meta.json").exists():
        sys.exit(f"run.py report: no run {run} in results/")
    return RESULTS / run


def print_header(r: Results):
    meta = r.meta
    source = meta["source"]
    if source == "commit" or not meta["uncommitted_sha256"]:
        source += f" @ {meta['commit'][:7]}"
    print(
        f"Run {meta['run_id']}   {meta['model']}, "
        f"effort {meta['effort']}, {source}"
    )

    accepted = sum(s["passed"] for s in r.step1.values())
    result = f"the fuzzer accepted {accepted}/{len(meta['functions'])}"
    if r.step2:
        end = r.step2["end"]
        result += (
            f"; testsuite {end['passed']}/{end['tests']} "
            f"after {r.step2['iterations']} attempt(s)"
        )
    else:
        result += "; step 2 not run"
    print(f"Result: {result}")
    print()


def main(argv: list[str]):
    args = parse_args(argv)
    r = Results.load(find_run(args.run))

    tables = {
        "step1": lambda: step1_table(r),
        "step2": lambda: step2_table(r) if r.step2 else None,
        "summary": lambda: summary_table(r),
    }
    names = [args.table] if args.table else TABLES

    if not args.csv:
        print_header(r)

    for name in names:
        table = tables[name]()
        if table is None:
            continue
        if args.csv:
            if len(names) > 1:
                print(f"# {name}")
            table.print_csv()
        else:
            table.print()
