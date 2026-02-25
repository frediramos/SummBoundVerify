#!/usr/bin/env python3

import sys
import traceback
from argparse import Namespace

from cli import parse_input_args
from validation_gen import ValidationGenerator, CCompiler


def compile_validation_test(arch, file: str, libs):
    bin_name = file[:-2] + '.test'  # Remove '.c' + .test
    comp = CCompiler(arch, file, bin_name, libs)
    comp.compile()
    return bin_name


# Takes command line / config file arguments
def run_validation_gen(args: Namespace):
    '''
    Take command line args and run the test generation
    @args: \'argparse\' Namespace object
    '''
    concrete_function = args.func
    target_summary = args.summ
    summname = args.summname
    funcname = args.funcname
    outputfile = args.o

    if not concrete_function and not target_summary:
        msg = "ERROR: At least the code for a concrete function or summary MUST be provided"
        sys.exit(msg)

    if not concrete_function and not funcname:
        msg = ("ERROR: No concrete function code or name provided\n"
               "INFO: In the absence of the code, a name must be specified in order to call the function")
        sys.exit(msg)

    if not target_summary and not summname:
        msg = ("ERROR: No summary code or name provided\n"
               "INFO: In the absence of the code, a name must be specified in order to call the summary")
        sys.exit(msg)

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

    file = valgenerator.gen()

    assert (file == outputfile)
    return file


def run_angr(binary: str, args: Namespace):

    from validation_tool import angrEngine

    engine = angrEngine(
        binary,
        timeout=args.timeout,
        results_dir=args.results,
        stats_dir=args.stats,
        convert_ascii=args.ascii,
        debug=args.debug
    )

    engine.run()


def main():
    try:
        # Parse all input (cli and config file)
        args = parse_input_args()

        # Run a given binary a exit
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

    except Exception as e:
        print(traceback.format_exc())
        print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
