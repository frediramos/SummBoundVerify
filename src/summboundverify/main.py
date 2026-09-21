import sys
import json
import logging
import traceback

from enum import Enum
from pathlib import Path
from argparse import Namespace

from summboundverify.exceptions import RunError
from summboundverify.options import parse_input_args
from summboundverify.logger import Colors, section, setup_logging

from summboundverify.utils import DescribedEnum
from summboundverify.validation_tool.fuzzing import afl_available

from . import se, fuzzing


logger = logging.getLogger(__name__)


class Engine(DescribedEnum):
    SE = ("se", "Symbolic execution (angr)")
    FUZZ = ("fuzz", "Fuzzing (AFL++)")


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
        rows.setdefault(test_id(key), {})[Engine.SE] = (
            se_verdict(entry)
        )

    for key, entry in fuzz.items():
        rows.setdefault(test_id(key), {})[Engine.FUZZ] = (
            fuzz_verdict(entry)
        )

    unknown = ("not run", Colors.white)
    width = max(len(name) for name in rows)

    section("Summary")

    for name, verdicts in rows.items():
        se_text, se_color = verdicts.get(
            Engine.SE,
            unknown,
        )
        fuzz_text, fuzz_color = verdicts.get(
            Engine.FUZZ,
            unknown,
        )

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


def plan_engines(args: Namespace) -> list[Engine]:
    engines = [Engine(e) for e in args.engine]

    if Engine.FUZZ in engines and not afl_available():
        raise RunError("AFL++ is not installed...")

    return engines


def main():
    try:
        args = parse_input_args()
        setup_logging(args.debug)

        # Run a given binary directly.
        if args.run and args.binary:
            se.run_angr(args.binary, args)
            return 0

        engines = plan_engines(args)

        results: dict[Engine, Path | None] = {}
        constraints = {}

        if Engine.SE in engines:
            section(Engine.SE.desc)
            results[Engine.SE], constraints = se.run(args)

        if Engine.FUZZ in engines:
            section(Engine.FUZZ.desc)

            results[Engine.FUZZ] = fuzzing.run(
                args,
                constraints,
            )

        if len(engines) > 1 and args.run:
            print_summary(
                results.get(Engine.SE),
                results.get(Engine.FUZZ),
            )

    except Exception:
        print(traceback.format_exc())
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
