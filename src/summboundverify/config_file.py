import re
import ast
import sys

from options import Options, OptionTypes


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

        if config_option in Options:
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

        else:
            print(f'[!] Unknown option \'{config_option}\' in {conf}')

    return config
