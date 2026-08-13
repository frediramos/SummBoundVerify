from dataclasses import dataclass
from pycparser.c_ast import NodeVisitor

from summboundverify.exceptions import (
    DuplicateFunctionDeclarationError,
    DuplicateFunctionDefinitionError
)

from pycparser.c_ast import Decl, FuncDecl, FuncDef, NodeVisitor


class ReturnTypeVisior(NodeVisitor):

    def __init__(self):
        self.name: str
        self.ptr = 0

    def get_ret(self):
        typ = self.name + self.ptr * '*'
        return typ

    def generic_visit(self, node):
        return node

    def visit(self, node):
        if node is not None:
            return NodeVisitor.visit(self, node)

    def visit_PtrDecl(self, node):
        self.ptr += 1
        self.visit(node.type)

    def visit_TypeDecl(self, node):
        self.visit(node.type)

    def visit_IdentifierType(self, node):
        self.name = node.names[0]


@dataclass
class Function:
    declaration: Decl
    definition: FuncDef | None = None

    @property
    def name(self) -> str:
        return self.declaration.name

    @property
    def args(self):
        return self.declaration.type.args

    @property
    def return_type(self):
        return self.declaration.type.type

    @property
    def body(self):
        return self.definition.body if self.definition else None


class FunctionVisitor(NodeVisitor):
    """
    Visit the ASt to separate each elemenet of interest function definitions; defined structs; and Typedefs
    """

    def __init__(self, ast, filename):

        self.file = filename
        self.ast = ast

        self._functions: dict[str, Function] = {}

    def functions(self):
        if not self._functions:
            self.visit(self.ast)
        return self._functions

    def fnames(self):
        return list(self.functions())

    def visit(self, node):
        if node is not None:
            return NodeVisitor.visit(self, node)

    def visit_Decl(self, node: Decl):
        if not isinstance(node.type, FuncDecl):
            return

        name = node.name
        function = self._functions.get(name)

        if function is None:
            self._functions[name] = Function(declaration=node)
        else:
            DuplicateFunctionDeclarationError(name, self.file)

    def visit_FuncDef(self, node: FuncDef):
        name = node.decl.name
        function = self._functions.get(name)

        if function is None:
            function = Function(
                declaration=node.decl,
                definition=node
            )
            self._functions[name] = function
        else:
            if function.definition is not None:
                raise DuplicateFunctionDefinitionError(name, self.file)
            else:
                function.definition = node


class FuncCallsVisitor(NodeVisitor):

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

    def visit_Cast(self, node):
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

    def visit_TernaryOp(self, node):
        self.visit(node.cond)
        self.visit(node.iftrue)
        self.visit(node.iffalse)
