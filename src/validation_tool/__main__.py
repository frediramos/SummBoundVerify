#!/usr/bin/env python3

import os
import sys
import traceback
import argparse

from .engine import angrEngine


def parse_cmd_args(progname, input=None):

    module_usage = f'python3 -m {progname}'
    parser = argparse.ArgumentParser(
        prog=module_usage, description='angr extension for summary testing/validation')

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


def main():
    prog = os.path.normpath(sys.argv[0]).split(os.sep)[-2]

    try:
        args = parse_cmd_args(prog)
        engine = angrEngine(
            args.binary,
            timeout=args.timeout,
            save_stats=args.stats,
            save_paths=args.save_paths,
            stats_dir=args.results,
            paths_dir=args.paths,
            convert_ascii=args.ascii,
            ignore=args.summ_ignore,
            debug=args.debug
        )

        engine.run()

    except Exception:
        print(traceback.format_exc(), end='')
        return 1
    return 0


sys.exit(main())
