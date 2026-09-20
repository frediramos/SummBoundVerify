import sys
import json
import logging
import traceback

from argparse import Namespace
from pathlib import Path

from summboundverify.exceptions import RunError
from summboundverify.logger import Colors, section, setup_logging
from summboundverify.options import parse_input_args

from . import se, fuzzing


logger = logging.getLogger(__name__)

ENGINE_TITLES = {
    "se": "Symbolic execution (angr)",
    "fuzz": "Fuzzing (AFL++)",
}


def load_results(path: Path | None) -> dict:
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def test_id(key: str) -> str:
    _, _, test = key.rpartition(".")
    return test or key


def se_verdict(entry: dict) -> tuple[str, str]:
    result = entry.get("result", "unknown")
    color = (
        Colors.green
        if result == "exact"
        else Colors.yellow
    )
    return result, color


def fuzz_verdict(entry: dict) -> tuple[str, str]:
    verdict = entry.get("verdict", "unknown")
    checked = entry.get("checked") or 0

    detail = (
        f" ({checked} sample(s))"
        if checked
        else ""
    )

    if verdict == "mismatched":
        findings = entry.get("findings") or []
        bindings = (
            findings[0].get("bindings")
            if findings
            else None
        )

        if bindings:
            detail += " [{}]".format(
                ", ".join(
                    f"{k}={v}"
                    for k, v in bindings.items()
                )
            )

        color = Colors.red

    elif verdict == "starved":
        color = Colors.yellow

    else:
        color = Colors.green

    return f"{verdict}{detail}", color


def print_summary(
    se_results: Path | None,
    fuzz_results: Path | None,
):
    se = load_results(se_results)
    fuzz = load_results(fuzz_results)

    if not se and not fuzz:
        return

    rows: dict[str, dict] = {}

    for key, entry in se.items():
        rows.setdefault(test_id(key), {})["se"] = (
            se_verdict(entry)
        )

    for key, entry in fuzz.items():
        rows.setdefault(test_id(key), {})["fuzz"] = (
            fuzz_verdict(entry)
        )

    unknown = ("not run", Colors.white)
    width = max(len(name) for name in rows)

    section("Summary")

    for name, verdicts in rows.items():
        se_text, se_color = verdicts.get("se", unknown)
        fuzz_text, fuzz_color = verdicts.get("fuzz", unknown)

        print(
            f"  {name:<{width}}"
            f"  symbolic: {se_color}{se_text:<12}{Colors.reset}"
            f"  fuzz: {fuzz_color}{fuzz_text}{Colors.reset}",
            file=sys.stderr,
        )

        if (
            se_text == "exact"
            and fuzz_text.startswith("mismatched")
        ):
            print(
                f"  {Colors.red}"
                "the engines disagree: one of them is wrong"
                f"{Colors.reset}",
                file=sys.stderr,
            )

        if fuzz_text.startswith("starved"):
            print(
                f"  {Colors.yellow}"
                "sampling checked nothing; its verdict "
                f"carries no weight{Colors.reset}",
                file=sys.stderr,
            )

    print(file=sys.stderr, flush=True)


def plan_engines(args: Namespace) -> list[str]:
    from summboundverify.validation_tool.se_support import (
        se_obstacles_in,
    )

    engines = (
        ["se", "fuzz"]
        if args.engine == "both"
        else [args.engine]
    )

    if "se" not in engines or not args.func:
        return engines

    obstacles = se_obstacles_in(
        args.func,
        args.funcname,
    )

    if not obstacles:
        return engines

    name = args.funcname or Path(args.func).stem

    engines = [
        engine
        for engine in engines
        if engine != "se"
    ]

    logger.warning(
        "Skipping symbolic execution: %s %s.\n"
        "angr cannot finish this target, so it would run "
        "until the timeout and report nothing.",
        name,
        "; ".join(obstacles),
    )

    if engines:
        return engines

    from summboundverify.validation_tool.fuzz_engine import (
        afl_available,
    )

    if not afl_available():
        raise RunError(
            f"Symbolic execution was skipped ({obstacles[0]}) "
            "and fuzzing, the engine that handles such targets, "
            "needs AFL++ (Debian/Ubuntu: apt install afl++). "
            "Nothing was validated."
        )

    logger.warning(
        "Falling back to fuzzing, the only engine left for %s",
        name,
    )

    return ["fuzz"]


def main():
    try:
        args = parse_input_args()
        setup_logging(args.debug)

        # Run a given binary directly.
        if args.run and args.binary:
            se.run_angr(args.binary, args)
            return 0

        engines = plan_engines(args)

        results: dict[str, Path | None] = {}
        constraints = {}

        if "se" in engines:
            if len(engines) > 1:
                section(ENGINE_TITLES["se"])

            results["se"], constraints = se.run(args)

        if "fuzz" in engines:
            if len(engines) > 1:
                section(ENGINE_TITLES["fuzz"])

            results["fuzz"] = fuzzing.run(
                args,
                constraints,
            )

        if len(engines) > 1 and args.run:
            print_summary(
                results.get("se"),
                results.get("fuzz"),
            )

    except Exception:
        print(traceback.format_exc())
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
