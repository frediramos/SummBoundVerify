"""Validation engines.

Imports are deferred: `angrEngine` pulls in angr, which is slow to import and
entirely unnecessary for a `--engine fuzz` run.
"""


def __getattr__(name):
    if name == 'angrEngine':
        from .engine import angrEngine
        return angrEngine

    if name == 'aflEngine':
        from .fuzz_engine import aflEngine
        return aflEngine

    if name in ('summary_formulas', 'validate_by_sampling', 'log_report'):
        from . import sampling
        return getattr(sampling, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'angrEngine', 'aflEngine',
    'summary_formulas', 'validate_by_sampling', 'log_report',
]
