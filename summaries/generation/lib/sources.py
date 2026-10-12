"""
Step 2 on its own (-step2): which step 1 runs its summaries come from.

Each summary in summaries/obtained/ must be one the fuzzer accepted in step 1
of a run in results/, and that run must have used the same model, effort and
inputs as this one. Otherwise the run stops.
"""

import json

from pathlib import Path

from .common import (
    HERE,
    REPO,
    Target,
    fail,
    sha256,
)

RESULTS = HERE / "results"

# What a step 1 run must share with this one
SAME = ("model", "effort")

# What may differ, with a warning
WARN = ("claude_version", "commit")


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def runs() -> list[Path]:
    """The runs in results/, latest first."""
    found = (p for p in RESULTS.iterdir() if (p / "meta.json").exists())
    return sorted(found, reverse=True)


def accepted(run: Path, target: Target) -> tuple[int, Path] | None:
    """The attempt, and its summary, the fuzzer accepted in a run, if any."""
    folder = run / "step1" / target.function
    if not (folder / "summary.json").exists():
        return None

    summary = read(folder / "summary.json")
    if not summary["passed"]:
        return None

    # The fuzzer accepted the last attempt
    number = summary["iterations"]
    return number, folder / f"summary-{number}.c"


def find_source(target: Target) -> dict | None:
    """
    The latest run whose step 1 accepted the summary now in
    summaries/obtained/, or None.
    """
    digest = sha256(REPO / target.summary)
    for run in runs():
        found = accepted(run, target)
        if found and sha256(found[1]) == digest:
            number, _ = found
            return {"run": run.name, "attempt": number, "sha256": digest}
    return None


def stop(problem: str, items: list):
    """Stops the run if there are `items`, listing them all."""
    if items:
        fail(f"{problem}:\n  " + "\n  ".join(map(str, items)))


def target_inputs(meta: dict, function: str) -> dict[str, str]:
    """A run's input hashes that concern `function`: its own, and shared."""
    return {
        path: digest
        for path, digest in meta["inputs_sha256"].items()
        if not path.startswith("targets/")
        or path.split("/")[1] == function
    }


def differences(meta: dict, function: str, source: dict) -> list[str]:
    """How the step 1 run of `function` differs from this one."""
    other = read(RESULTS / source["run"] / "meta.json")
    where = f"{function} (run {source['run']})"

    found = [
        f"{where}: {key} {other[key]}, here {meta[key]}"
        for key in SAME
        if other[key] != meta[key]
    ]

    theirs = target_inputs(other, function)
    ours = target_inputs(meta, function)
    for path in sorted(theirs.keys() | ours.keys()):
        if theirs.get(path) != ours.get(path):
            found.append(f"{where}: {path} changed since")

    for key in WARN:
        if other[key] != meta[key]:
            print(f"warning: {where}: {key} {other[key]}, here {meta[key]}")

    return found


def find(targets: list[Target], meta: dict) -> dict[str, dict]:
    """
    Each target's step 1 run, attempt and summary hash, for meta.json.
    Stops if a run differs from this one, as described by `meta`.
    """
    missing = [t.summary for t in targets if not (REPO / t.summary).exists()]
    stop("no summaries yet; run step 1 for them first", missing)

    found = {t.function: find_source(t) for t in targets}
    unknown = [t.summary for t in targets if found[t.function] is None]
    stop(
        "summaries the fuzzer accepted in step 1 of no run in results/ "
        "(edited by hand, or changed by a step 2?)",
        unknown
    )

    sources = {fn: source for fn, source in found.items() if source}
    problems = [
        problem
        for function, source in sources.items()
        for problem in differences(meta, function, source)
    ]
    stop("step 1 ran differently for some summaries", problems)

    return sources
