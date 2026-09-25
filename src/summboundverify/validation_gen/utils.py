from pathlib import Path

from pycparser import parse_file as pycparser_parse_file
from pycparser.c_ast import (
    Decl,
    Return,
    UnaryOp,
    Constant,
    ExprList,
    TypeDecl,
    FuncDecl,
    ArrayRef,
    Assignment,
    IdentifierType,
)
from pycparser.c_parser import ParseError

from summboundverify.utils.files import fake_libc_path, tmp_file
from summboundverify.exceptions import FileParseError


class Macros:
    MAX_NUM = "MAX_NUM"
    ARRAY_SIZE = "ARRAY_SIZE"
    FNAME_SIZE = "FNAME_SIZE"

    POINTER_SIZE = "POINTER_SIZE"
    FUEL = "FUEL"


DEFINED_MACROS: dict[str, int] = {}


def add_fake_include(file):
    """Copy `file` with a `#include <stdlib.h>` prepended, and return the copy.

    Input files routinely use `size_t`, `NULL` and friends without including
    anything, which pycparser cannot parse on its own. The include pulls those
    in from the fake libc headers. The caller owns the temporary file.
    """
    fake_include = '#include <stdlib.h>\n'
    tmp = tmp_file(f"__{Path(file).name}")
    tmp.write_text(fake_include + Path(file).read_text())
    return tmp


def parse_c_file(file):
    """Parse a C source file the way the generator does.

    Anything that reads a *user-supplied* C file must go through this rather
    than `parse_file`, which assumes the file is already self-contained.
    """
    tmp = add_fake_include(file)
    try:
        return parse_file(tmp)
    finally:
        tmp.unlink(missing_ok=True)


def parse_file(file):
    try:
        fakelib = fake_libc_path()
        ast = pycparser_parse_file(
            file, use_cpp=True,
            cpp_path='gcc',
            cpp_args=['-E', f'-I{fakelib}']  # type: ignore
        )
        return ast
    except ParseError as e:
        raise FileParseError(file, e)


def define_macro(label: str, value: int):
    DEFINED_MACROS[label] = value
    return f'#define {label} {value}'


def get_defined_macro(label: str):
    return DEFINED_MACROS[label]


def define_include(name):
    return f'#include <{name}>'


def return_value(val, operator=None):
    if operator:
        val = UnaryOp(operator, val)
    expr = ExprList([val])
    return Return(expr)


def create_function(name, args, returnType):
    typedecl = TypeDecl(name, [], None, IdentifierType(names=[returnType]))
    funcdecl = FuncDecl(args, typedecl)
    decl = Decl(name, [], [], [], [], funcdecl, None, None)
    return decl


def fill_array(lvalue, rvalue, index):
    arr_lvalue = ArrayRef(lvalue, subscript=index)
    assign = Assignment(op='=', lvalue=arr_lvalue, rvalue=rvalue)
    return assign


def terminate_string(lvalue, index):
    return fill_array(lvalue, Constant('char', '\'\\0\''), index)
