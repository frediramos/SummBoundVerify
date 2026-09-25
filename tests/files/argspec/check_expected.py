#!/usr/bin/env python3
"""Compare a fuzz check report with the verdicts a test expects.

Usage: check_expected.py <check.json> <expected_result.json>

expected_result.json maps each test to the verdict the fuzz engine should
reach: "passed" for a correct summary, "mismatched" for one that is wrong on
purpose.

    {"test_1": {"verdict": "passed"}}
"""

import json
import sys
from pathlib import Path


def main(check_path: str, expected_path: str) -> int:
    check = Path(check_path)
    if not check.exists():
        print(f"no report at {check}: the fuzz engine did not finish")
        return 1

    actual = json.loads(check.read_text())
    expected = json.loads(Path(expected_path).read_text())
    status = 0

    for test, want in expected.items():
        got = actual.get(test, {}).get('verdict', 'missing')
        if got != want['verdict']:
            print(f"{test}: expected {want['verdict']}, got {got}")
            status = 1

    return status


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
