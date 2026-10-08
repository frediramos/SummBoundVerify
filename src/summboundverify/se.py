import logging

from pathlib import Path
from argparse import Namespace

from summboundverify.argspec import load_argspec, extract_constraints
from summboundverify.validation_gen import (
    Arch,
    CCompiler,
    SymbolicValidationGenerator,
)

logger = logging.getLogger(__name__)


def compile_validation_test(arch: Arch, file: Path, libs: list[str]) -> Path:
    name = file.stem + ".test"
    out = file.parent / name

    compiler = CCompiler(arch, file, out, libs)
    compiler.compile()

    return out


def generate_test(args: Namespace, outputfile: Path | None = None) -> Path:

    concrete_function = Path(args.func) if args.func else None
    target_summary = Path(args.summ) if args.summ else None
    outputfile = Path(outputfile) if outputfile else Path(args.o)

    if not concrete_function and not target_summary:
        raise ValueError(
            "At least the code for a concrete function or summary "
            "MUST be provided"
        )

    if not concrete_function and not args.funcname:
        raise ValueError(
            "No concrete function code or name provided\n"
            "INFO: pass -func <file>, or --libc to compare against "
            "a libc function"
        )

    if not target_summary and not args.summname:
        raise ValueError(
            "No summary code or name provided\n"
            "INFO: In the absence of the code, a name must be "
            "specified in order to call the summary"
        )

    argspec = load_argspec(getattr(args, 'argspec', None))
    constraints = extract_constraints(argspec)

    generator = SymbolicValidationGenerator(
        concrete_function,
        target_summary,
        outputfile,
        arraysize=constraints.get('arraysize', [5]),
        nullbytes=constraints.get('nullbytes', []),
        maxnum=constraints.get('maxnum', []),
        maxnames=constraints.get('maxnames', []),
        default=constraints.get('defaults', {}),
        concrete_arrays=constraints.get('concrete_arrays', {}),
        no_api=args.noapi,
        cncrt_name=args.funcname,
        summ_name=args.summname,
        argspec=argspec,
    )

    generator.gen()

    return outputfile


def run_angr(binary: str | Path, args: Namespace) -> tuple[Path, dict]:
    from summboundverify.validation_tool import AngrEngine

    binary = Path(binary)

    engine = AngrEngine(
        binary,
        timeout=args.timeout,
        results_dir=args.results,
        stats_dir=args.stats,
        convert_ascii=args.ascii,
    )

    engine.run()

    results = (
        Path(args.results)
        / f"{binary.name}_result.json"
    )

    return results, engine.constraints


def run(args: Namespace) -> tuple[Path | None, dict]:
    if not args.compile:
        return None, {}

    test = generate_test(args)

    binary = compile_validation_test(
        args.compile,
        test,
        args.lib,
    )

    if not args.run:
        return None, {}

    return run_angr(binary, args)
