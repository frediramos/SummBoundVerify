from .cli import parse_cmdline_args

from .options import (
    Options,
    OptionTypes
)

from .parser import parse_config_file


def parse_input_args(input=None):

    args = parse_cmdline_args(input)

    config_file = args.config
    if config_file:
        config = parse_config_file(config_file)
        for c in config.keys():
            setattr(args, c, config[c])

    return args
