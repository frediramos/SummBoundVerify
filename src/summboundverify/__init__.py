"""SummBoundVerify public API."""

from summboundverify.validation_gen import ValidationGenerator
from summboundverify.validation_gen import CCompiler as ValidationCompiler


def __getattr__(name):
    # Deferred so that importing the package does not pull in angr.
    if name in ('ValidationRunner', 'AngrEngine'):
        from summboundverify.validation_tool import AngrEngine
        return AngrEngine

    if name in ('FuzzRunner', 'AflEngine'):
        from summboundverify.validation_tool import AflEngine
        return AflEngine

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'ValidationGenerator',
    'ValidationCompiler',
    'ValidationRunner',
    'FuzzRunner',
]
