import logging
from pathlib import Path
from argparse import Namespace

from summboundverify.exceptions import RunError
from summboundverify.validation_gen import (
    SummaryFuzzGenerator,
    ConcreteFuzzGenerator,
)

logger = logging.getLogger(__name__)


def sampler_libs(args: Namespace) -> list[str]:
    """
    Return the libraries needed by the concrete sampling harness.

    The summary library is excluded when it is identifiable by the
    summary function name.
    """
    from summboundverify.validation_gen.utils import parse_c_file
    from summboundverify.validation_gen.parser import FunctionVisitor

    libs = list(args.lib or [])

    if not args.summname:
        return libs

    keep = []

    for lib in libs:
        path = Path(lib)

        try:
            defined = FunctionVisitor(parse_c_file(path), path).functions()
        except Exception:
            keep.append(lib)
            continue

        if args.summname in defined:
            logger.debug(
                "Not linking %s into the sampler: it is the summary",
                path.name,
            )
            continue

        keep.append(lib)

    return keep


def outputfiles(args: Namespace) -> tuple[Path, Path]:
    """Return the summary and concrete fuzz-test output paths."""

    out = Path(args.o)

    return (
        out.with_name(f"{out.stem}-summary{out.suffix}"),
        out.with_name(f"{out.stem}-concrete{out.suffix}"),
    )


def _load_argspec(args: Namespace) -> tuple[dict, dict]:
    from summboundverify.argspec import load_argspec, extract_constraints
    spec = load_argspec(getattr(args, 'argspec', None))
    return spec, extract_constraints(spec)


def generate_summary_test(args: Namespace, outputfile: Path) -> Path:
    concrete_function = Path(args.func) if args.func else None
    target_summary = Path(args.summ) if args.summ else None

    argspec, constraints = _load_argspec(args)

    generator = SummaryFuzzGenerator(
        concrete_function,
        target_summary,
        outputfile,
        arraysize=constraints.get('arraysize', [5]),
        nullbytes=constraints.get('nullbytes', []),
        maxnum=constraints.get('maxnum', []),
        maxnames=constraints.get('maxnames', []),
        default=constraints.get('defaults', {}),
        concrete_arrays=constraints.get('concrete_arrays', {}),
        cncrt_name=args.funcname,
        summ_name=args.summname,
        no_api=args.noapi,
        argspec=argspec,
    )

    generator.gen()

    return outputfile


def generate_concrete_test(args: Namespace, outputfile: Path) -> Path:
    concrete_function = Path(args.func) if args.func else None
    target_summary = Path(args.summ) if args.summ else None

    argspec, constraints = _load_argspec(args)

    generator = ConcreteFuzzGenerator(
        concrete_function,
        target_summary,
        outputfile,
        arraysize=constraints.get('arraysize', [5]),
        nullbytes=constraints.get('nullbytes', []),
        maxnum=constraints.get('maxnum', []),
        maxnames=constraints.get('maxnames', []),
        default=constraints.get('defaults', {}),
        concrete_arrays=constraints.get('concrete_arrays', {}),
        cncrt_name=args.funcname,
        summ_name=args.summname,
        no_api=args.noapi,
        argspec=argspec,
    )

    generator.gen()

    return outputfile


def run(args: Namespace, constraints: dict | None = None) -> Path | None:
    """
    Generate and optionally run the two fuzzing halves.

    If constraints were produced by symbolic execution in the same
    invocation, reuse them instead of executing the summary again.
    """
    from summboundverify.validation_tool.fuzzing import sampling

    summary_test, concrete_test = outputfiles(args)
    constraints = constraints or {}

    arch = args.compile or "x86"

    if not constraints:
        generate_summary_test(args, summary_test)

        constraints = sampling.summary_formulas(
            summary_test,
            libs=args.lib,
            arch=arch,
            timeout=args.timeout,
            results_dir=args.results,
        )

    generate_concrete_test(args, concrete_test)

    if not args.run:
        return None

    try:
        results, _ = sampling.validate_by_sampling(
            concrete_test,
            constraints,
            libs=sampler_libs(args),
            arch=arch,
            execs=args.execs,
            timeout=args.timeout,
            results_dir=args.results,
        )
    except ValueError as exc:
        raise RunError(str(exc))

    sampling.log_report(results)

    out = (
        Path(args.results)
        / f"{concrete_test.stem}_check.json"
    )

    sampling.write_report(results, out)

    logger.info("Sample check written to %s", out)

    return out
