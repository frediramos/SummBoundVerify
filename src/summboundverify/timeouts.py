"""
A run's three timeouts, in seconds:

    timeout       the whole run
    se_timeout    each symbolic execution (the se engine, and the summary's
                  symbolic run when fuzzing): a summary that takes longer
                  most likely has too many paths
    fuzz_timeout  each AFL++ campaign

A stage gets its own limit, cut to what is left of the whole run's. Without
one, it gets what is left.
"""

import time

from argparse import Namespace

from summboundverify.exceptions import RunError


def start(args: Namespace):
    """Starts the whole run's clock."""
    args.deadline = time.monotonic() + args.timeout


def stage(args: Namespace, limit: int | None) -> int:
    """
    The timeout of a stage whose own limit is `limit`. Raises RunError if
    the whole run is out of time.
    """
    deadline = getattr(args, "deadline", None)
    if deadline is None:
        return limit or args.timeout

    left = int(deadline - time.monotonic())
    if left < 1:
        raise RunError(f"The run timed out after {args.timeout} seconds")

    return min(limit, left) if limit else left
