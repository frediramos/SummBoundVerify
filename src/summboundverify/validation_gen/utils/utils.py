from os.path import dirname, realpath
from os.path import join as join_path

from pycparser import parse_file
from pycparser.c_ast import *

SIZE_MACRO = 'SIZE'
MAX_MACRO = 'MAX_NUM'
ARRAY_SIZE_MACRO = 'ARRAY_SIZE'
POINTER_SIZE_MACRO = 'POINTER_SIZE'
FUEL_MACRO = 'FUEL'
FAKE_LIBC = join_path(dirname(realpath(__file__)), '..',
                      '..', 'Fake_libc', 'fake_libc_include')


def parseFile(file, fakelib=FAKE_LIBC):
    ast = parse_file(file, use_cpp=True,
                     cpp_path='gcc',
                     cpp_args=['-E', f'-I{fakelib}'])
    return ast


def defineMacro(label, value):
    return f'#define {label} {value}\n'


def defineInclude(name):
    return f'#include <{name}>\n'


def returnValue(val, operator=None):
    if operator:
        val = UnaryOp(operator, val)
    expr = ExprList([val])
    return Return(expr)


def createFunction(name, args, returnType):
    typedecl = TypeDecl(name, [], None, IdentifierType(names=[returnType]))
    funcdecl = FuncDecl(args, typedecl)
    decl = Decl(name, [], [], [], [], funcdecl, None, None)
    return decl


def mainFunction(calls):
    calls_ast = [c for c in map(
        lambda x: FuncCall(ID(x), ExprList([])), calls)]
    calls_ast.append(returnValue(Constant('int', str(0))))
    block = Compound(calls_ast)
    return block


def fill_array(lvalue, rvalue, index):
    arr_lvalue = ArrayRef(lvalue, subscript=index)
    assign = Assignment(op='=', lvalue=arr_lvalue, rvalue=rvalue)
    return assign


def terminate_string(lvalue, index):
    return fill_array(lvalue, Constant('char', '\'\\0\''), index)


class FCallsVisitor(NodeVisitor):

    def __init__(self):
        self.calls = []

    def fcalls(self):
        return list(set(self.calls))

    def generic_visit(self, node):
        return node

    def visit(self, node):
        if node is not None:
            return NodeVisitor.visit(self, node)

    def visit_Assignment(self, node):
        self.visit(node.lvalue)
        self.visit(node.rvalue)

    def visit_Switch(self, node):
        self.visit(node.cond)
        self.visit(node.stmt)

    def visit_Return(self, node):
        self.visit(node.expr)

    def visit_Case(self, node):
        self.visit(node.expr)
        if node.stmts is not None:
            for stmt in node.stmts:
                self.visit(stmt)

    def visit_UnaryOp(self, node):
        self.visit(node.expr)

    def visit_BinaryOp(self, node):
        self.visit(node.left)
        self.visit(node.right)

    def visit_Compound(self, node):
        block = node.block_items
        if block is not None:
            for stmt in node.block_items:
                self.visit(stmt)
        return node

    def visit_Decl(self, node):
        self.visit(node.init)
        return node

    def visit_FuncDecl(self, node):
        args = node.args
        if args is not None:
            for decl in args.params:
                self.visit(decl)
        return node

    def visit_FuncDef(self, node):
        self.visit(node.decl.type)
        self.visit(node.body)
        return node

    def visit_ExprList(self, node):
        exprs = node.exprs
        if exprs is not None:
            for expr in exprs:
                self.visit(expr)
        return node

    def visit_FuncCall(self, node):
        self.calls.append(node.name.name)
        self.visit(node.args)
        return node

    def visit_If(self, node):
        self.visit(node.cond)
        self.visit(node.iftrue)
        self.visit(node.iffalse)
        return node

    def visit_While(self, node):
        self.visit(node.cond)
        self.visit(node.stmt)
        return node

    def visit_For(self, node):
        self.visit(node.init)
        self.visit(node.stmt)
        self.visit(node.cond)
        return node
