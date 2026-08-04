"""Concrete backend for the validation API.

The C sources here implement the same API the angr SimProcedures implement,
so a generated test can be linked into a native binary and executed on
concrete inputs instead of symbolically.
"""

from pathlib import Path

CONCRETE_DIR = Path(__file__).resolve().parent

RUNTIME_HEADER = CONCRETE_DIR / 'sbv_runtime.h'
RUNTIME_SOURCE = CONCRETE_DIR / 'sbv_runtime.c'
DRIVER_SOURCE = CONCRETE_DIR / 'driver.c'

# The generated test's main() is renamed so the driver can own the real one.
TEST_ENTRY = 'sbv_run_tests'

__all__ = [
    'CONCRETE_DIR',
    'RUNTIME_HEADER',
    'RUNTIME_SOURCE',
    'DRIVER_SOURCE',
    'TEST_ENTRY',
]
