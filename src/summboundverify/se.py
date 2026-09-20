import logging

from pathlib import Path
from argparse import Namespace

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
            "INFO: In the absence of the code, a name must be "
            "specified in order to call the function"
        )

    if not target_summary and not args.summname:
        raise ValueError(
            "No summary code or name provided\n"
            "INFO: In the absence of the code, a name must be "
            "specified in order to call the summary"
        )

    generator = SymbolicValidationGenerator(
        concrete_function,
        target_summary,
        outputfile,
        arraysize=args.arraysize,
        nullbytes=args.nullbytes,
        maxnum=args.maxvalue,
        maxnames=args.maxnames,
        default=args.defaultvalues,
        concrete_arrays=args.concretearray,
        memory=args.memory,
        no_api=args.noapi,
        cncrt_name=args.funcname,
        summ_name=args.summname,
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
