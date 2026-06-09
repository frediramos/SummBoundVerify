from pycparser.c_ast import NodeVisitor


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
