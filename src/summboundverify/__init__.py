"""SummBoundVerify public API."""

from summboundverify.validation_gen import ValidationGenerator
from summboundverify.validation_gen import CCompiler as ValidationCompiler


def __getattr__(name):
    # Deferred so that importing the package does not pull in angr.
    if name in ('ValidationRunner', 'angrEngine'):
        from summboundverify.validation_tool import angrEngine
        return angrEngine

    if name in ('FuzzRunner', 'fuzzEngine'):
        from summboundverify.validation_tool import fuzzEngine
        return fuzzEngine

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'ValidationGenerator',
    'ValidationCompiler',
    'ValidationRunner',
    'FuzzRunner',
]
