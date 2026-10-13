#!/usr/bin/env python3
"""
Tables of generation runs in results/, for the paper.

    ./run.py report                        the latest run: its three tables
    ./run.py report 2026-10-12_09-15-00    a given run
    ./run.py report RUN RUN ...            several runs, pieced together:
                                           e.g. step 1 done in parts
    ./run.py report --table step2          one table: step1, step2 or summary
    ./run.py report -csv                   raw values as CSV, e.g. for plots

`./lib/report.py` takes the same arguments.

The tables:
    step1    one row per function: the attempts until the fuzzer accepted
             its summary, and their cost
    step2    one row per testsuite run: tests passed, overall and per suite,
             the summaries the attempt before it changed, and its cost
    summary  one row per function: its fuzzer runs (step 1, then each change
             in step 2) and its testsuite runs until its suite passed (-:
             never), with step 1's cost; then step 2's cost, and the total

A -step2 run's step 1 rows come from the runs its summaries come from.

Columns:
    model time  the model's time (duration_api_ms)
    wall time   the attempts' whole time: the claude call, then the checks
                (the fuzzer; in step 2, the testsuite too)
    turns       the model's requests, summed over the calls (num_turns)
    tokens      tokens consumed: every request's new input (uncached and
                written to cache) and output, thinking included; input read
                from cache, i.e. resent, is left out
    cost        what the calls cost (total_cost_usd)
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
    Column("turns", "turns"),
    Column("tokens", "tokens", tokens),
    Column("cost_usd", "cost", dollars),
]


def wall(record: dict, *parts: float) -> float:
    """
    An attempt's or a step's whole time. Runs from before it was recorded
    give its parts instead: the claude calls' time, then the checks'.
    """
    return record.get("time_s", sum(parts))


def step1_wall(totals: dict) -> float:
    return wall(totals, totals["wall_s"], totals["fuzzer_time_s"])


def step2_wall(totals: dict) -> float:
    return wall(
        totals,
        totals["wall_s"],
        totals["fuzzer_time_s"],
        totals["testsuite_time_s"]
    )


def cost(claude: dict, wall_s: float) -> dict:
    """
    A row's cost columns, from a call's metrics or summed ones, and the
    whole time.
    """
    return {
        "api_s": (claude["duration_api_ms"] or 0) / 1000,
        "wall_s": wall_s,
        "turns": int(claude["num_turns"] or 0),
        "tokens": (
            claude["input_tokens"]
            + claude["cache_creation_input_tokens"]
            + claude["output_tokens"]
        ),
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
    metas: list[dict]               # each run's meta.json
    step1: dict[str, dict]          # each function's summary.json
    step1_iters: dict[str, list]    # each function's iter-<n>.json
    step2: dict | None              # step 2's summary.json
    step2_runs: list[dict]          # testsuite records: start, then each
    step2_iters: list[dict]

    @classmethod
    def load(cls, folder: Path) -> "Results":
        meta = read(folder / "meta.json")
        functions = meta["functions"]

        # A -step2 run's step 1 is in the runs its summaries come from
        sources = meta.get("step1_sources", {})

        step1 = {}
        step1_iters = {}
        for fn in functions:
            run = RESULTS / sources[fn]["run"] if fn in sources else folder
            summary = run / "step1" / fn / "summary.json"
            if summary.exists():
                step1[fn] = read(summary)
                step1_iters[fn] = iterations(run / "step1" / fn)

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
            [meta],
            step1,
            step1_iters,
            step2,
            step2_runs,
            step2_iters
        )

    @classmethod
    def merge(cls, runs: list["Results"], prog: str) -> "Results":
        """
        Several runs as one, in the order given: a function's step 1 comes
        from the last run that has it, and step 2 from the one run that has
        it.
        """
        with_step2 = [r for r in runs if r.step2]
        if len(with_step2) > 1:
            ids = ", ".join(r.metas[0]["run_id"] for r in with_step2)
            sys.exit(f"{prog}: more than one run has a step 2: {ids}")

        merged = cls([], {}, {}, None, [], [])
        for r in runs:
            merged.metas += r.metas
            merged.step1.update(r.step1)
            merged.step1_iters.update(r.step1_iters)
        for r in with_step2:
            merged.step2 = r.step2
            merged.step2_runs = r.step2_runs
            merged.step2_iters = r.step2_iters
        return merged

    @property
    def functions(self) -> list[str]:
        """The functions the runs covered."""
        return sorted({fn for m in self.metas for fn in m["functions"]})


# -- The tables --------------------------------------------------------------

def step1_table(r: Results) -> Table:
    rows = [
        {
            "target": fn,
            "passed": "yes" if s["passed"] else "no",
            "attempts": s["iterations"],
            **cost(s["totals"], step1_wall(s["totals"])),
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
        if number == 0:
            row["wall_s"] = run["time_s"]
        else:
            it = r.step2_iters[number - 1]
            fuzzer = sum(c["time_s"] for c in it["fuzzer"].values())
            whole = wall(it, it["claude"]["wall_s"], fuzzer, run["time_s"])
            row["changed"] = ", ".join(it["changed"])
            row.update(cost(it["claude"], whole))
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
            **cost(s["totals"], step1_wall(s["totals"])),
        })

    runs = len(r.step2_runs) or None
    if r.step2:
        rows.append({
            "target": "testsuite",
            "testsuite_runs": runs,
            **cost(r.step2["totals"], step2_wall(r.step2["totals"])),
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

def parse_args(argv: list[str], prog: str) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        prog=prog,
        description=__doc__.split("\n\n")[0]
    )
    ap.add_argument(
        "runs",
        nargs="*",
        metavar="run",
        help="runs in results/, e.g. 2026-10-12_09-15-00, or the paths to "
             "their folders, reported as one (default: the latest)"
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


def find_runs(names: list[str], prog: str) -> list[Path]:
    """The runs' folders, or the latest run's."""
    runs = sorted(p for p in RESULTS.glob("*") if (p / "meta.json").exists())
    if not runs:
        sys.exit(f"{prog}: no runs in results/")
    if not names:
        return runs[-1:]

    folders = []
    for name in names:
        # A run's name, or the path to its folder
        folder = Path(name) if Path(name).is_dir() else RESULTS / name
        if not (folder / "meta.json").exists():
            sys.exit(f"{prog}: no run {name} in results/")
        folders.append(folder)
    return folders


def print_run(meta: dict):
    source = meta["source"]
    if source == "commit" or not meta["uncommitted_sha256"]:
        source += f" @ {meta['commit'][:7]}"
    print(
        f"Run {meta['run_id']}   {meta['model']}, "
        f"effort {meta['effort']}, {source}"
    )


def print_header(r: Results):
    for meta in r.metas:
        print_run(meta)

    accepted = sum(s["passed"] for s in r.step1.values())
    result = f"the fuzzer accepted {accepted}/{len(r.functions)}"
    if r.step2:
        end = r.step2["end"]
        result += (
            f"; testsuite {end['passed']}/{end['tests']} "
            f"after {r.step2['iterations']} attempt(s)"
        )
    else:
        result += "; step 2 not run"
    print(f"Result: {result}")

    for meta in r.metas:
        sources = meta.get("step1_sources")
        if sources:
            runs = sorted({s["run"] for s in sources.values()})
            print(f"Step 1 of {meta['run_id']} from: {', '.join(runs)}")
    print()


def main(argv: list[str], prog: str = "report.py"):
    args = parse_args(argv, prog)
    runs = [Results.load(f) for f in find_runs(args.runs, prog)]
    r = Results.merge(runs, prog)

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


if __name__ == "__main__":
    main(sys.argv[1:])
