from pathlib import Path

from pycparser import parse_file
from pycparser.c_parser import ParseError
from pycparser.c_generator import CGenerator

from pycparser.c_ast import (
    FileAST,
    Compound,
    Constant,
    FuncDef,
    Return,
    TypeDecl,
)

from summboundverify.utils.files import fake_libc_path
from summboundverify.utils.visitors import FunctionVisitor

from summboundverify.exceptions import FileParseError


def parse_api(sra: Path, *includes: Path) -> FileAST:

    fakelib = str(fake_libc_path())
    include_list = [f'-include{i}' for i in includes]

    try:
        ast = parse_file(
            str(sra),
            use_cpp=True,
            cpp_path="gcc",
            cpp_args=['-E', f'-I{fakelib}'] + include_list  # type: ignore
        )
        return ast
    except ParseError as e:
        raise FileParseError(sra, e)


def _make_stub(function) -> str:
    decl = function.declaration
    return_type = decl.type.type

    returns_void = (
        isinstance(return_type, TypeDecl)
        and return_type.type.names == ["void"]
    )

    if returns_void:
        body = Compound(block_items=[])
    else:
        body = Compound(
            block_items=[
                Return(
                    expr=Constant(
                        type="int",
                        value="0",
                    )
                )
            ]
        )

    fdef = FuncDef(decl=decl, param_decls=[], body=body)
    generator = CGenerator()
    code = generator.visit(fdef)
    formatted = " ".join(code.split())
    return formatted


def get_stubs(file: Path, types: Path) -> dict[str, str]:

    stubs = {}
    ast = parse_api(file, types)

    functions = FunctionVisitor(ast, file).functions()
    for name, node in functions.items():
        stub = _make_stub(node)
        stubs[name] = stub

    return stubs


def get_code(file: Path) -> list[str]:
    ast = parse_api(file)
    generator = CGenerator()
    code = generator.visit(ast)
    formatted = code.strip().split('\n')
    return formatted
