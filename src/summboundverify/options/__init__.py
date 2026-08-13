from .cli import parse_cmdline_args

from .options import (
    Options,
    OptionTypes
)

from .parser import (
    eval_ast,
    parse_config_file
)


# Options that are used as numbers rather than passed along as text. argparse
# coerces them on the command line; the config file parser returns every
# `SIMPLE` option as a string, so `timeout 60` in a config reaches
# `sp.run(timeout='60')` and raises TypeError before the campaign starts.
NUMERIC = ('execs', 'timeout')


def parse_input_args(input=None):

    # Parse command line args
    args = parse_cmdline_args(input)
    complex = [OptionTypes.NESTED, OptionTypes.DICT]

    # Convert complex options string to Python ast
    for opt in filter(lambda a: a[2] in complex, Options):
        parsed = eval_ast(getattr(args, opt[1]))
        setattr(args, opt[1], parsed)

    # Parse config file and override cmd args
    config_file = args.config
    if config_file:
        config = parse_config_file(config_file)
        for c in config.keys():
            setattr(args, c, config[c])

        for option in NUMERIC:
            value = getattr(args, option, None)
            if isinstance(value, str):
                setattr(args, option, int(value))

    return args
