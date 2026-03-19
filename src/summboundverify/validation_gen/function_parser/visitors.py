from pycparser.c_ast import *

# Visit the ASt to separate each elemenet of interest
# function definitions; defined structs; and Typedefs


class ReturnTypeVisior(NodeVisitor):
    def __init__(self):
        self.name = None
        self.ptr = 0

    def get_ret(self):
        typ = self.name + self.ptr*'*'
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


class FunctionVisitor(NodeVisitor):

    def __init__(self, ast, filename):

        self.file = filename
        self.ast = ast

        self._functions = {}
        self._function_args = {}

    def functions(self):
        if not self._functions:
            self.visit(self.ast)

        return self._functions

    def function_names(self):
        if not self._functions:
            self.visit(self.ast)

        return list(self._functions.keys())

    def function_args(self):
        if not self._function_args:
            self.visit(self.ast)

        return self._function_args

    def visit(self, node):
        if node is not None:
            return NodeVisitor.visit(self, node)

    def visit_FuncDef(self, node):
        name = node.decl.name
        if name in self._functions.keys():
            sys.exit(
                f"ERROR: Mutiple functions with same name in: \'{self.file}\'")

        self._functions[node.decl.name] = node
        self._function_args[node.decl.name] = node.decl.type.args.params if node.decl.type.args else None
