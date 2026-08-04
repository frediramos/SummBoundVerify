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

from summboundverify.utils.files import current_dir
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


def define_macro(label, value):
    return f'#define {label} {value}'


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
