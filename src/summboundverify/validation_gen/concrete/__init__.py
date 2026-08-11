from pathlib import Path

CONCRETE_DIR = Path(__file__).resolve().parent

DRIVER_SOURCE = CONCRETE_DIR / 'driver.c'

# The generated test's main() is renamed so the driver can own the real one.
TEST_ENTRY = 'sbv_run_tests'

__all__ = [
    'CONCRETE_DIR',
    'DRIVER_SOURCE',
]
