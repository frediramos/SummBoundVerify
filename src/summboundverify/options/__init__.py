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

    resolve_libc(args)

    return args


def resolve_libc(args):
    """Point ``funcname`` at the libc function selected by ``--libc``.

    ``--libc`` alone reuses the summary name; ``--libc name`` names the
    libc function explicitly. The function is resolved at link time, so
    it cannot be combined with ``-func``.
    """

    if not args.libc:
        return

    if args.func:
        raise ValueError("--libc and -func are mutually exclusive")

    name = args.libc if isinstance(args.libc, str) else args.summname
    if not name:
        raise ValueError("--libc needs a function name or --summname")

    if args.funcname and args.funcname != name:
        raise ValueError(
            f"--libc '{name}' conflicts with --funcname '{args.funcname}'"
        )

    args.funcname = name
