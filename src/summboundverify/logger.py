import sys
import logging


class Colors():
    red = "\033[31m"
    green = "\033[32m"
    yellow = "\033[33m"
    teal = "\033[36m"
    white = "\033[37m"
    wred = "\033[41m"  # White text, red background
    reset = "\033[0m"


LOGGING_COLORS = {
    logging.DEBUG: Colors.white,
    logging.INFO: Colors.teal,
    logging.WARNING: Colors.yellow,
    logging.ERROR: Colors.red,
    logging.CRITICAL: Colors.wred,
}


class FriendlyFormatter(logging.Formatter):

    def format(self, record):
        levelname = record.levelname
        name = record.name

        # Style level name
        color = LOGGING_COLORS.get(record.levelno, "")
        styled_level = levelname.lower().capitalize()
        record.levelname = f"{color}{styled_level}{Colors.reset}"

        # Style logger name
        record.name = f"{Colors.green}{name}{Colors.reset}"
        return super().format(record)


def section(title: str, color: str = Colors.teal) -> None:
    '''Announce a new stage of the run.

    Written to stderr rather than printed: that is where the log handler
    writes, and mixing the two streams reorders the output as soon as it is
    piped (stdout is block-buffered, stderr is not).
    '''
    bar = '=' * (len(title) + 4)
    print(
        f"\n{color}{bar}\n  {title}\n{bar}{Colors.reset}\n",
        file=sys.stderr,
        flush=True,
    )


def format_string(debug: bool):
    if debug:
        return "(%(name)s) %(levelname)s %(message)s"
    return "(%(levelname)s) %(message)s"


def config_third_party(debug: bool) -> None:
    info_or_error = logging.INFO if debug else logging.ERROR
    warning_or_error = logging.INFO if debug else logging.ERROR

    levels = {
        "angr": info_or_error,
        "claripy": info_or_error,
        "cle": warning_or_error,
        "pyvex": logging.ERROR,
    }

    for name, lvl in levels.items():
        logging.getLogger(name).setLevel(lvl)


def setup_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    root = logging.getLogger()
    root.handlers.clear()

    root.setLevel(level)

    handler = logging.StreamHandler()

    handler.setFormatter(
        FriendlyFormatter(format_string(debug))
    )

    root.addHandler(handler)
    config_third_party(debug)
