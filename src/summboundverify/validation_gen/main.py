import sys
import logging
from argparse import Namespace

from summboundverify.logger import setup_logging
from summboundverify.validation_gen.validation import ValidationGenerator
from summboundverify.validation_gen.c_compiler import CCompiler
from summboundverify.validation_gen.cli import parse_input_args


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
        sys.exit(
            'ERROR: At least the code for a concrete function or summary MUST be provided')

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


def main():
    args = parse_input_args()

    level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level)

    test = run_validation_gen(args)
    if args.compile:
        arch = args.compile
        libs = args.lib
        compile_validation_test(arch, test, libs)

    return 0
