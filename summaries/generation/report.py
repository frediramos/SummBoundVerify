#!/usr/bin/env python3
"""
Tables of the generation runs in results/, for the paper.

    ./report.py                 every run
    ./report.py read            one function's runs
    ./report.py -attempts       one row per attempt instead of per run
    ./report.py -csv            raw values as CSV, e.g. for plots

Columns:
    attempts    claude -p calls (the attempt's number, with -attempts)
    model time  the model's time (duration_api_ms)
    wall time   the claude calls' time, tools included; fuzzing excluded
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
from statistics import median
from tabulate import tabulate
from dataclasses import dataclass

signal.signal(signal.SIGPIPE, signal.SIG_DFL)

RESULTS = Path(__file__).resolve().parent / "results"


# ── Formatting ──────────────────────────────────────────────────────────────

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


@dataclass
class Column:
    key: str
    header: str
    fmt: Callable = str
    numeric: bool = True


COLUMNS = [
    Column("function", "function", numeric=False),
    Column("run", "run", numeric=False),
    Column("passed", "passed", numeric=False),
    Column("attempts", "attempts"),
    Column("api_s", "model time", duration),
    Column("wall_s", "wall time", duration),
    Column("turns", "turns", lambda n: f"{n:.0f}"),
    Column("input_tokens", "input", tokens),
    Column("output_tokens", "output", tokens),
    Column("cost_usd", "cost", dollars),
]


def print_table(rows: list[dict]):
    cells = [
        [
            col.fmt(row[col.key]) if col.numeric else str(row[col.key])
            for col in COLUMNS
        ]
        for row in rows
    ]
    table = tabulate(
        cells,
        headers=[col.header for col in COLUMNS],
        colalign=["right" if col.numeric else "left" for col in COLUMNS],
        disable_numparse=True
    )
    print(table)


# ── Results ─────────────────────────────────────────────────────────────────

def row(function: str, run: str, passed, attempts: int, claude: dict) -> dict:
    """One table row, from the metrics of an attempt or a run's totals."""
    return {
        "function": function,
        "run": run,
        "passed": passed,
        "attempts": attempts,
        "api_s": (claude["duration_api_ms"] or 0) / 1000,
        "wall_s": claude["wall_s"],
        "turns": claude["num_turns"] or 0,
        "input_tokens": (
            claude["input_tokens"]
            + claude["cache_creation_input_tokens"]
            + claude["cache_read_input_tokens"]
        ),
        "output_tokens": claude["output_tokens"],
        "cost_usd": claude["cost_usd"] or 0,
    }


def load_runs(functions: list[str]):
    """Each finished run in results/: its folder and its summary.json."""
    for fn_dir in sorted(RESULTS.glob("*")):
        if functions and fn_dir.name not in functions:
            continue
        for run_dir in sorted(fn_dir.glob("*")):
            summary = run_dir / "summary.json"
            if summary.exists():
                yield run_dir, json.loads(summary.read_text())


def run_rows(runs) -> list[dict]:
    return [
        row(
            s["function"],
            s["run_id"],
            "yes" if s["passed"] else "no",
            s["iterations"],
            s["totals"]
        )
        for _, s in runs
    ]


def attempt_rows(runs) -> list[dict]:
    rows = []
    for run_dir, s in runs:
        files = sorted(
            run_dir.glob("iter-*.json"),
            key=lambda p: int(p.stem.split("-")[1])
        )

        for f in files:
            it = json.loads(f.read_text())
            rows.append(
                row(
                    s["function"],
                    s["run_id"],
                    "yes" if it["passed"] else "no",
                    it["iteration"],
                    it["claude"]
                )
            )
    return rows


def median_rows(rows: list[dict]) -> list[dict]:
    """The median of each column per function. Not shown for now."""
    medians = []
    for fn in sorted({r["function"] for r in rows}):
        runs = [r for r in rows if r["function"] == fn]
        passed = sum(r["passed"] == "yes" for r in runs)
        medians.append({
            "function": fn,
            "run": f"median of {len(runs)}",
            "passed": f"{passed}/{len(runs)}",
            **{
                col.key: median(r[col.key] for r in runs)
                for col in COLUMNS if col.numeric
            },
        })
    return medians


# ── Main ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "functions",
        nargs="*",
        help="only these functions (default: all)"
    )
    ap.add_argument(
        "-attempts",
        action="store_true",
        help="one row per attempt instead of per run"
    )
    ap.add_argument(
        "-csv",
        action="store_true",
        help="print raw values as CSV"
    )
    return ap.parse_args()


def print_csv(rows: list[dict]):
    writer = csv.DictWriter(sys.stdout, [col.key for col in COLUMNS])
    writer.writeheader()
    writer.writerows(rows)


def main():
    args = parse_args()

    runs = list(load_runs(args.functions))
    if not runs:
        sys.exit("report.py: no runs in results/")

    rows = attempt_rows(runs) if args.attempts else run_rows(runs)

    if args.csv:
        print_csv(rows)
    else:
        print_table(rows)


if __name__ == "__main__":
    main()
