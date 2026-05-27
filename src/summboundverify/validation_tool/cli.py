import argparse


def parse_cmd_args(input=None):

    parser = argparse.ArgumentParser(
        prog='summval', description='Validate summaries using angr'
    )

    group1 = parser.add_argument_group('General')
    group2 = parser.add_argument_group('Summary Validation')

    group1.add_argument('binary', metavar='bin', type=str,
                        help='Path to the target binary')

    group1.add_argument('-stats', action='store_true',
                        help='Save execution statistics in a Json file', default=False)

    group1.add_argument('--results', metavar='path', type=str,
                        help='Directory where outputs should saved (default: ./)', default='.')

    group1.add_argument('--timeout', metavar='sec', type=int,
                        help='Execution Timeout in seconds (default: 1800sec, 30min)', default=30*60)

    group1.add_argument('-debug', action='store_true',
                        help='Enable debug logging to console')

    parser.add_argument('-save_paths', action='store_true',
                        help='Save the created symvars to a file', default=False)

    parser.add_argument('--paths', metavar='path', type=str,
                        help='Directory where the paths should be saved (default: ./)', default='.')

    group1.add_argument('--summ_ignore', metavar='file', type=str,
                        help='Do NOT use summaries for functions in the given input file', default=None)

    group2.add_argument('-ascii', action='store_true',
                        help='Convert ASCII values to characters in counterexamples')

    return parser.parse_args(input)
