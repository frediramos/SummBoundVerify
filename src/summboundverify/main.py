import sys
import traceback

from pathlib import Path
from typing import Literal
from argparse import Namespace

from summboundverify.logger import setup_logging
from summboundverify.options import parse_input_args
from summboundverify.validation_gen import ValidationGenerator, CCompiler

Arch = Literal['x86', 'x64']


def compile_validation_test(arch: Arch, file: Path, libs: list[str]):
    name = file.stem + '.test'
    out = file.parent / name
    comp = CCompiler(arch, file, out, libs)
    comp.compile()
    return out


# Takes command line / config file arguments
def run_validation_gen(args: Namespace, engine: str = 'se',
                       outputfile: Path | None = None):
    '''
    Take command line args and run the test generation
    @args: \'argparse\' Namespace object
    @engine: which backend the test is emitted for ('se' or 'fuzz')
    @outputfile: override for the generated test path
    '''
    concrete_function = Path(args.func) if args.func else None
    target_summary = Path(args.summ) if args.summ else None
    outputfile = Path(outputfile) if outputfile else Path(args.o)
    summname = args.summname
    funcname = args.funcname

    if not concrete_function and not target_summary:
        err = "ERROR: At least the code for a concrete function or summary MUST be provided"
        sys.exit(err)

    if not concrete_function and not funcname:
        err = (
            "ERROR: No concrete function code or name provided\n"
            "INFO: In the absence of the code, a name must be specified in order to call the function"
        )
        sys.exit(err)

    if not target_summary and not summname:
        err = (
            "ERROR: No summary code or name provided\n"
            "INFO: In the absence of the code, a name must be specified in order to call the summary"
        )
        sys.exit(err)

    valgenerator = ValidationGenerator(
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
        cncrt_name=funcname,
        summ_name=summname,
        no_api=args.noapi,
        engine=engine,
    )

    valgenerator.gen()
    return outputfile


def run_angr(binary: Path, args: Namespace):

    from summboundverify.validation_tool import angrEngine

    engine = angrEngine(
        binary,
        timeout=args.timeout,
        results_dir=args.results,
        stats_dir=args.stats,
        convert_ascii=args.ascii,
    )

    engine.run()


def run_fuzz(test: Path, args: Namespace):

    from summboundverify.validation_tool import fuzzEngine

    engine = fuzzEngine(
        test,
        libs=args.lib,
        arch=args.compile or 'x86',
        execs=args.execs,
        timeout=args.timeout,
        results_dir=args.results,
    )

    engine.run()


def run_se(test: Path, args: Namespace):

    if not args.compile:
        return

    binary = compile_validation_test(args.compile, test, args.lib)

    if args.run:
        run_angr(binary, args)


def fuzz_outputfile(args: Namespace) -> Path:
    """Keep the two engines' generated tests side by side in a `both` run."""
    out = Path(args.o)
    if args.engine != 'both':
        return out
    return out.with_name(f'{out.stem}-fuzz{out.suffix}')


def main():
    try:
        # Parse all input (cli and config file)
        args = parse_input_args()

        setup_logging(args.debug)

        # Run a given binary and exit
        if args.run and args.binary:
            run_angr(args.binary, args)
            return 0

        engines = ['se', 'fuzz'] if args.engine == 'both' else [args.engine]

        for engine in engines:

            if engine == 'se':
                test = run_validation_gen(args, engine='se')
                run_se(test, args)

            else:
                test = run_validation_gen(
                    args, engine='fuzz', outputfile=fuzz_outputfile(args)
                )
                # The fuzz engine links the test against the concrete backend
                # itself, so compilation is part of its run.
                if args.run:
                    run_fuzz(test, args)

    except Exception as e:
        print(traceback.format_exc())
        print(e)
        return 1

    return 0
