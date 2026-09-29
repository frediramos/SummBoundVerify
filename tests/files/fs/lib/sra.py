#!/usr/bin/env python3

from pathlib import Path
from summboundverify.api import make_lib


def dot():
    return Path(__file__).resolve().parent


if __name__ == "__main__":
    print(f"Creating the Symbolic Reflection API library...")
    make_lib(dot())  # make_lib('.')
