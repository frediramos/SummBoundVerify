import argparse

from .options import Options


def parse_cmdline_args(input=None):

    def flag(option: tuple):
        return f'{option[0]}{option[1]}'

    parser = argparse.ArgumentParser(
        prog='summbv', description='Generate Summary Validation Tests'
    )

    generation = parser.add_argument_group('Test Generation')
    validation = parser.add_argument_group('Validation')

    generation.add_argument(flag(Options.o), metavar='name', type=str, required=False, default='test.c',
                            help='Test output name')

    generation.add_argument(flag(Options.func), metavar='file', type=str,
                            help='Path to file containing the concrete function')

    generation.add_argument(flag(Options.summ), metavar='file', type=str,
                            help='Path to file containing the target summary')

    generation.add_argument(flag(Options.summname), metavar='name', type=str,
                            help='Name of the summary in the given path')

    generation.add_argument(flag(Options.funcname), metavar='name', type=str,
                            help='Name of the concrete function in the given path')

    generation.add_argument(flag(Options.lib), metavar='path', nargs='+', type=str, required=False,
                            help='Path to external files needed to compile the test binary')

    generation.add_argument(flag(Options.noapi), action='store_true',
                            help='Do not include the Validation API stubs')

    generation.add_argument(flag(Options.compile), const='x86', choices=['x86', 'x64'], nargs='?',
                            help='Compile the generated test')

    generation.add_argument(flag(Options.argspec), metavar='path', type=str, required=False, default=None,
                            help='YAML file describing argument semantics and constraints')

    generation.add_argument(flag(Options.config), metavar='path', type=str, required=False,
                            help='YAML config file')

    validation.add_argument(flag(Options.engine), metavar='name', nargs='+', choices=['se', 'fuzz'], default=['se'],
                            help='Validation engine: se (symbolic execution) or fuzz (fuzzing) (default: se)')

    validation.add_argument(flag(Options.execs), metavar='n', type=int, default=10000,
                            help='Number of inputs to try when fuzzing (default: 10000)')

    validation.add_argument(flag(Options.run), action='store_true',
                            help='Run the generated test')

    validation.add_argument(flag(Options.binary), metavar='bin', type=str, default=None,
                            help='Path to a previously generated binary')

    validation.add_argument(flag(Options.timeout), metavar='sec', type=int,
                            help='Execution Timeout in seconds (default: 1800sec, 30min)', default=30*60)

    validation.add_argument(flag(Options.results), metavar='path', type=str,
                            help='Directory where JSON results should be saved (default: ./)', default='.')

    validation.add_argument(flag(Options.stats), metavar='path', type=str,
                            help='Directory to save execution statistics', default=None)

    validation.add_argument(flag(Options.ascii), action='store_true',
                            help='Convert ASCII values to characters in counterexamples')

    validation.add_argument(flag(Options.debug), action='store_true',
                            help='Enable debug logging to console')

    args = parser.parse_args(input)

    assert len(vars(args)) == len(Options)
    return args
