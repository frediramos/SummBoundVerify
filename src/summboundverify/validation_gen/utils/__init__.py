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

from summboundverify.utils.files import current_dir, tmp_file
from summboundverify.exceptions import FileParseError

SIZE_MACRO = 'SIZE'
FUEL_MACRO = 'FUEL'
MAX_MACRO = 'MAX_NUM'
ARRAY_SIZE_MACRO = 'ARRAY_SIZE'
POINTER_SIZE_MACRO = 'POINTER_SIZE'


def fake_libc_path():
    path = current_dir(__file__) / "fake_libc_include"
    if not path.is_dir():
        err = "Could not locate pycparser fake_libc_include"
        raise RuntimeError(err)
    return path


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


def defineMacro(label, value):
    return f'#define {label} {value}'


def defineInclude(name):
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
