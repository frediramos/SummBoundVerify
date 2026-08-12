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
def run_validation_gen(args: Namespace):
    '''
    Take command line args and run the test generation
    @args: \'argparse\' Namespace object
    '''
    concrete_function = Path(args.func) if args.func else None
    target_summary = Path(args.summ) if args.summ else None
    outputfile = Path(args.o)
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
        no_api=args.noapi
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


def main():
    try:
        # Parse all input (cli and config file)
        args = parse_input_args()

        setup_logging(args.debug)

        # Run a given binary and exit
        if args.run and args.binary:
            run_angr(args.binary, args)
            return 0

        # Gen validation test
        test = run_validation_gen(args)

        # Compile
        if args.compile:
            arch = args.compile
            libs = args.lib
            binary = compile_validation_test(arch, test, libs)

            # Run if specified
            if args.run:
                run_angr(binary, args)

    except Exception:
        print(traceback.format_exc())
        return 1

    return 0
