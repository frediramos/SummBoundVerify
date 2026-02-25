import re
import ast
import sys
import argparse
import traceback
from argparse import Namespace

from .validation import ValidationGenerator
from .c_compiler import CCompiler


class OptionTypes:

    BOOL = 'boolean'
    SIMPLE = 'simple'
    LIST = 'list'
    NESTED = 'nested'
    DICT = 'dict'


class Options():

    # Validate option defs just in case
    # 1 - check that class attributes and option names match
    # 2 - check that all used types are define in OptionTypes
    def validate_options(self):
        for name, opt in self.__dict__.items():
            optname = opt[1]
            opttype = opt[2]
            assert opttype in vars(OptionTypes).values()
            assert name == optname, f'option names must match => self.{name} != {optname}'

    def __init__(self) -> None:
        self.o = ('-', 'o', OptionTypes.SIMPLE)
        self.func = ('-', 'func', OptionTypes.SIMPLE)
        self.summ = ('-', 'summ', OptionTypes.SIMPLE)
        self.summname = ('--', 'summname', OptionTypes.SIMPLE)
        self.funcname = ('--', 'funcname', OptionTypes.SIMPLE)
        self.arraysize = ('--', 'arraysize', OptionTypes.NESTED)
        self.nullbytes = ('--', 'nullbytes', OptionTypes.NESTED)
        self.defaultvalues = ('--', 'defaultvalues', OptionTypes.NESTED)
        self.maxvalue = ('--', 'maxvalue', OptionTypes.LIST)
        self.maxnames = ('--', 'maxnames', OptionTypes.LIST)
        self.concretearray = ('--', 'concretearray', OptionTypes.DICT)
        self.lib = ('--', 'lib', OptionTypes.LIST)
        self.noapi = ('-', 'noapi', OptionTypes.BOOL)
        self.compile = ('--', 'compile', OptionTypes.SIMPLE)
        self.memory = ('-', 'memory', OptionTypes.BOOL)
        self.config = ('-', 'config', OptionTypes.SIMPLE)

        self.validate_options()

    def values(self):
        return list(self.__dict__.values())

    def names(self):
        return [opt[1] for opt in self.__dict__.values()]


Options = Options()


def _get_simple(line: str):
    tokens = line.split()
    opt = tokens[0]

    if len(tokens) != 2:
        msg = f'Option {opt} in config file takes exactly one argument'
        sys.exit(msg)

    if '{' in line or '[' in line:
        msg = f'Option {opt} in config file takes a simple argument (non-list, non-dict)'
        sys.exit(msg)

    return opt, tokens[1]


def parse_boolean(line: str):
    opt, arg = _get_simple(line)
    arg = arg.capitalize()

    if not (arg == 'True' or arg == 'False'):
        msg = f'Option {opt} in config file takes a boolean value (true/false)'
        sys.exit(msg)

    return ast.literal_eval(arg)


def parse_simple(line: str):
    _, arg = _get_simple(line)
    return arg


def parse_dict(line):
    if '{' in line:
        value_sets = re.findall(r'(\{[^\}]*\})+', line)
        return list(map(lambda x: ast.literal_eval(x), value_sets))


def parse_nested_list(line):
    if '[' in line:
        size_sets = re.findall(r'(\[[^\]]*\])+', line)
        return list(map(lambda x: ast.literal_eval(x), size_sets))
    else:
        return parse_simple_list(line)


def parse_simple_list(line):
    tokens = line.split()
    opt = tokens[0]

    if '[' in line:
        msg = f'Option {opt} in config file takes a simple list (non-nested)'
        sys.exit(msg)

    return list(map(lambda x: int(x) if x.isnumeric() else x, tokens[1:]))


def read_config_file(file: str):
    with open(file, "r") as f:
        lines = f.readlines()
        return lines


def parse_config_file(conf) -> dict:

    lines = read_config_file(conf)
    config = {}

    for l in lines:
        l = l.strip()

        if l.startswith('//'):
            continue

        tokens = l.split()
        assert len(tokens) >= 2
        config_option = tokens[0]

        if config_option in Options.names():
            *_, option_type = getattr(Options, config_option)

            if option_type == OptionTypes.BOOL:
                arg = parse_boolean(l)
            elif option_type == OptionTypes.SIMPLE:
                arg = parse_simple(l)
            elif option_type == OptionTypes.LIST:
                arg = parse_simple_list(l)
            elif option_type == OptionTypes.NESTED:
                arg = parse_nested_list(l)
            else:
                assert option_type == OptionTypes.DICT
                arg = parse_dict(l)

            config[config_option] = arg

    return config


def parse_cmd_args(input=None):

    def flag(option: tuple):
        return f'{option[0]}{option[1]}'

    parser = argparse.ArgumentParser(
        prog='summvb', description='Generate Summary Validation Tests')

    parser.add_argument(flag(Options.o), metavar='name', type=str, required=False, default='test.c',
                        help='Test output name')

    parser.add_argument(flag(Options.func), metavar='file', type=str,
                        help='Path to file containing the concrete function')

    parser.add_argument(flag(Options.summ), metavar='file', type=str,
                        help='Path to file containing the target summary')

    parser.add_argument(flag(Options.summname), metavar='name', type=str,
                        help='Name of the summary in the given path')

    parser.add_argument(flag(Options.funcname), metavar='name', type=str,
                        help='Name of the concrete function in the given path')

    parser.add_argument(flag(Options.arraysize), metavar='value | [val1,val2]', nargs='+', required=False, default=[5],
                        help='Maximum array size of each test (default:5)')

    parser.add_argument(flag(Options.nullbytes), metavar='index | [idx1,idx2]', nargs='+', required=False, default=[],
                        help='Specify array indexes to place null bytes')

    parser.add_argument(flag(Options.defaultvalues), metavar='{var:value}', nargs='+', required=False, default={},
                        help='Specify default const values for input variables')

    parser.add_argument(flag(Options.maxvalue), metavar='value', nargs='+', required=False, default=[],
                        help='Provide an upper bound for numeric values')

    parser.add_argument(flag(Options.maxnames), metavar='name', nargs='+', required=False, default=[],
                        help='Numeric value names to be constrained')

    parser.add_argument(flag(Options.concretearray), metavar='{var:[indexes]}', nargs='+', required=False, default={},
                        help='Place concrete values in selected array indexes')

    parser.add_argument(flag(Options.lib), metavar='path', nargs='+', type=str, required=False,
                        help='Path to external files needed to compile the test binary')

    parser.add_argument(flag(Options.noapi), action='store_true',
                        help='Do not include the Validation API stubs')

    parser.add_argument(flag(Options.compile), const='x86', choices=['x86', 'x64'], nargs='?',
                        help='Compile the generated test')

    parser.add_argument(flag(Options.memory), action='store_true',
                        help='Evaluate a summary with memory manipulation side-effects')

    parser.add_argument(flag(Options.config), metavar='path', type=str, required=False,
                        help='Config file')

    args = parser.parse_args(input)

    assert len(vars(args)) == len(vars(Options))
    return args


def eval_ast(array):
    if array and isinstance(array[0], str):
        if '[' in array[0] or '{' in array[0]:
            return list(map(lambda x: ast.literal_eval(x), array))
    return array


def parse_input_args(input=None):

    # Parse command line args
    args = parse_cmd_args(input)
    options = Options.values()
    complex = [OptionTypes.NESTED, OptionTypes.DICT]

    # Convert complex options string to Python ast
    for opt in filter(lambda a: a[2] in complex, options):
        parsed = eval_ast(getattr(args, opt[1]))
        setattr(args, opt[1], parsed)

    # Parse config file and override cmd args
    config_file = args.config
    if config_file:

        config = parse_config_file(config_file)
        for c in config.keys():
            setattr(args, c, config[c])

    return args


def compileValidationTest(arch, file: str, libs):
    bin_name = file[:-2] + '.test'  # Remove '.c' + .test
    comp = CCompiler(arch, file, bin_name, libs)
    comp.compile()
    return bin_name


# Takes command line / config file arguments
def runValidationGen(args: Namespace):
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
    try:
        args = parse_input_args()
        test = runValidationGen(args)
        if args.compile:
            arch = args.compile
            libs = args.lib
            compileValidationTest(arch, test, libs)

    except Exception as e:
        print(traceback.format_exc())
        print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
