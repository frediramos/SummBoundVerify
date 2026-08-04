"""Validation engines.

Imports are deferred: `angrEngine` pulls in angr, which is slow to import and
entirely unnecessary for a `--engine fuzz` run.
"""


def __getattr__(name):
    if name == 'angrEngine':
        from .engine import angrEngine
        return angrEngine

    if name == 'fuzzEngine':
        from .fuzz_engine import fuzzEngine
        return fuzzEngine

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ['angrEngine', 'fuzzEngine']
