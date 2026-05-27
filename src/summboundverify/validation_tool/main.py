import logging

from summboundverify.logger import setup_logging
from summboundverify.validation_tool.engine import angrEngine
from summboundverify.validation_tool.cli import parse_cmd_args


def main():
    args = parse_cmd_args()

    level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level)

    engine = angrEngine(
        args.binary,
        timeout=args.timeout,
        results_dir=args.results,
        stats_dir=args.stats,
        paths_dir=args.paths,
        convert_ascii=args.ascii,
        ignore=args.summ_ignore,
        debug=args.debug
    )

    engine.run()
    return 0
