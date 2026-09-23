from pathlib import Path
from functools import cache
from types import SimpleNamespace

from summboundverify.utils.files import (
    write_file,
    read_file,
    current_dir
)

from .helpers import get_stubs, get_code

PREFIX = "__"

REQUIRED_FUNCTIONS = [
    "_ULE_",
    "assume",
    "save_current_state",
    "get_cnstr",
    "store_cnstr",
    "halt_all",
    "check_implications",
    "print_counterexamples",
    "mem_addr",
    "sym_var_array",
    "sym_var_named",
    "file_addr",
    "file_create",
    "file_open",
    "file_write",
    "file_set_offset",
]

CURRENT = current_dir(__file__)


class APIFiles:
    sra = CURRENT / "sra.h"
    validation = CURRENT / "validation.h"

    sra_types = CURRENT / "sra_types.h"
    stub_types = CURRENT / "stub_types.h"

    macros = CURRENT / "macros.h"


@cache
def symbolic_reflection_api() -> str:
    """Returns the symbolic reflection API file."""
    return APIFiles.sra.read_text()


@cache
def validation_api() -> str:
    """Returns the validation API file."""
    return APIFiles.validation.read_text()


@cache
def full_api() -> str:
    """Returns the full API."""
    return symbolic_reflection_api() + "\n" + validation_api()


@cache
def macros() -> str:
    """Returns the contents of the API macros file."""
    return APIFiles.macros.read_text()


@cache
def type_stubs() -> list[str]:
    """Returns the type stubs required by the API functions."""
    return get_code(APIFiles.sra_types, APIFiles.stub_types)


@cache
def sra_stubs() -> dict[str, str]:
    """
    Returns the stubs for the Symbolic Reflection API functions (excluding validation).
    """
    return get_stubs(
        APIFiles.sra,
        APIFiles.sra_types,
        APIFiles.stub_types
    )


@cache
def validation_stubs() -> dict[str, str]:
    """
    Returns the stubs for the validation API functions.
    """
    return get_stubs(
        APIFiles.validation,
        APIFiles.sra_types,
        APIFiles.stub_types
    )


@cache
def all_stubs() -> dict[str, str]:
    """
    Returns the stubs for all API functions.
    """
    return sra_stubs() | validation_stubs()


@cache
def required_stubs() -> dict[str, str]:
    """
    Returns the stubs for all required API functions.
    """
    stubs = all_stubs()
    required = {}
    for req in REQUIRED_FUNCTIONS:
        name = req
        if not (name.startswith(PREFIX)) and not (name.startswith('_')):
            name = PREFIX + name
        required[name] = stubs[name]
    return required


@cache
def api_map() -> SimpleNamespace:
    """
    Returns a mapping from required API names to their actual API names (prefixed).

    Raises:
        ValueError: If a required function is not defined in the API stubs.
    """

    stubs = all_stubs()
    values = {}

    for func in REQUIRED_FUNCTIONS:
        name = func
        if not (name.startswith(PREFIX)) and not (name.startswith('_')):
            name = PREFIX + name

        if name not in stubs:
            raise ValueError(
                f"Required function {func!r} not found in "
                f"{APIFiles.sra} or {APIFiles.validation}"
            )

        values[func] = name

    return SimpleNamespace(**values)


SRA_C = "sra.c"
SRA_H = "sra.h"


def make_lib(directory: str | Path, mkdir=True):
    d = Path(directory)

    macros_ = macros()
    types = '\n'.join(type_stubs())
    decls = read_file(APIFiles.sra)
    functions = '\n'.join(sra_stubs().values())

    hcode = (
        f"#ifndef SRA_H\n"
        f"#define SRA_H\n\n"
        f"{macros_}\n"
        f"{types}\n"
        f"{decls}\n"
        "#endif\n"
    )

    ccode = (
        f"#include \"{SRA_H}\"\n\n"
        f"{functions}\n"
    )

    write_file(d / SRA_H, hcode, mkdir=mkdir)
    write_file(d / SRA_C, ccode, mkdir=mkdir)
