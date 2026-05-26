import logging

COLORS = {
    logging.DEBUG: "\033[37m",
    logging.INFO: "\033[36m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[41m",
}

RESET = "\033[0m"


class FriendlyFormatter(logging.Formatter):

    def format(self, record):
        original = record.levelname
        styled = original.lower().capitalize()
        color = COLORS.get(record.levelno, "")
        record.levelname = (
            f"{color}{styled}{RESET}"
        )
        return super().format(record)


def setup_logging(level: int):
    root = logging.getLogger()
    root.handlers.clear()

    root.setLevel(level)

    handler = logging.StreamHandler()

    handler.setFormatter(
        FriendlyFormatter(
            "(%(levelname)s) %(message)s"
        )
    )

    root.addHandler(handler)
