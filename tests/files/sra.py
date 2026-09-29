#!/usr/bin/env python3
import sys

from pathlib import Path
from summboundverify.api import make_lib


if __name__ == "__main__":
    path = Path(sys.argv[1])

    print(f"Creating the Symbolic Reflection API library")
    files = make_lib(path)

    for f in files:
        print(f"file: {f}")
