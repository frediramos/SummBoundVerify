from pycparser.c_ast import *

from ....utils import returnValue, parseFile, createFunction
from ..generators.struct_fields import ArrayFieldGen, PrimitiveFieldGen, StructFieldGen, PtrFieldGen


# Generates the functions to init symbolic structs
class StructVisitor(NodeVisitor):
    def __init__(self, file: str):

        self.structs = {}
        self.aliases = {}
        self.structDefs = []

        if file:
            ast = parseFile(file)
            vis = StructParser()
            vis.visit(ast)

            self.structs = vis.getStructs()
            self.aliases = vis.getAliases()
            self.structDefs = vis.getDefs()

    # Arguments of init function
    # only 'fuel' arg so far
    # create_struct_X(fuel)
    def init_args(self):
        args = []

        typedecl = TypeDecl('fuel', [], None, IdentifierType(names=['int']))
        decl = Decl('fuel', [], [], [], [], typedecl, None, None)

        args.append(decl)
        return args

    # Allocate memory for struct
    # malloc(sizeof(struct))

    def malloc_struct(self, struct_name):

        typ = f'struct {struct_name}'
        name = f'struct_{struct_name}_instance'

        lvalue = TypeDecl(name, [], None, IdentifierType(names=[typ]))
        rvalue = FuncCall(ID('malloc'), ExprList([FuncCall(ID('sizeof'),
                                                           ExprList([ID(typ)]))]))

        # Assemble declaration
        decl = Decl(name, [], [], [], [], PtrDecl([], lvalue), rvalue, None)

        return decl

    def init_function(self, struct_name, fields, structs, aliases):

        if fields is None:
            return

        # Fuel parameter
        paramlist = ParamList(self.init_args())

        # Create a function declaration with name 'create_<struct_name>'
        decl = createFunction(name=f'create_struct_{struct_name}',
                              args=paramlist,
                              returnType=f'struct {struct_name}')

        code = []
        code.append(self.malloc_struct(struct_name))

        # Visit fields
        for field in fields:

            vis = StructFieldsVisitor(
                struct_name, field.name, structs, aliases)
            vis.visit(field)

            code += vis.code

        # Return struct
        code.append(returnValue(ID(f'struct_{struct_name}_instance'), '*'))

        # Create a block containg the function code
        block = Compound(code)

        # Place the block inside a function definition
        n_func_def_ast = FuncDef(decl, None, block, None)

        return n_func_def_ast

    # Create functions do instantiate all structs

    def symbolic_structs(self):

        code = [s for s in map(lambda x: self.init_function(
            x, self.structs[x], self.structs, self.aliases),
            self.structs) if s is not None]

        return self.structDefs + code


class StructParser(NodeVisitor):

    def __init__(self):

        # Typedefed structs
        self.aliases = {}
        self.structs = {}
        self.structDefs = []

    def getStructs(self):
        return self.structs

    def getAliases(self):
        return self.aliases

    def getDefs(self):
        return self.structDefs

    def visit(self, node):
        if node is not None:
            return NodeVisitor.visit(self, node)

    def visit_PtrDecl(self, node):
        self.visit(node.type)

    def visit_Struct(self, node):
        if node.decls is not None:
            self.structs[node.name] = node.decls
            self.structDefs.append(node)

    def visit_Typedef(self, node):
        visitor = TypeDefVisitor()

        self.aliases[node.name] = visitor.visit(node.type)
        self.visit(node.type)


class TypeDefVisitor(NodeVisitor):
    def __init__(self):
        self.ptr = False

    def visit(self, node):
        if node is not None:
            return NodeVisitor.visit(self, node)

    def visit_PtrDecl(self, node):
        self.ptr = True
        return self.visit(node.type)

    def visit_TypeDecl(self, node):
        return self.visit(node.type)

    def visit_Struct(self, node):
        return (node.name, self.ptr)

    def visit_IdentifierType(self, node):
        return (node.names[0], self.ptr)


# Visit the Struct fields and gen the appropriate symbolic values
class StructFieldsVisitor(NodeVisitor):

    def __init__(self, struct_name, field, structs, aliases):

        self.structs = structs
        self.aliases = aliases

        self.struct_name = struct_name
        self.field = field

        # ID object
        self.argname = None
        self.argtype = None

        # Array properties
        self.sizes = []

        # Struct properties
        self.struct = False

        self.ptr = False

        # Final line(s) of code
        self.code = []

    # Visitors
    def visit(self, node):
        return NodeVisitor.visit(self, node)

    # Entry Node
    def visit_Decl(self, node):
        self.argname = ID(name=node.name)
        self.visit(node.type)
        return

    # TypeDecl (Common node)
    def visit_TypeDecl(self, node):
        self.visit(node.type)

        if len(self.sizes) == 0:
            if self.struct:
                generator = StructFieldGen(self.argname, self.argtype,
                                           self.struct_name, self.field)
                self.code = generator.gen()
                return
            else:
                generator = PrimitiveFieldGen(self.argname, self.argtype,
                                              self.struct_name, self.field)
                self.code = generator.gen()
                return

        else:
            if self.ptr:
                generator = PtrFieldGen(self.argname, self.argtype, self.struct_name,
                                        self.field, self.sizes, self.struct)
                self.code = generator.gen()
                return

            else:
                generator = ArrayFieldGen(self.argname, self.argtype, self.struct_name,
                                          self.field, self.sizes, self.struct)
                self.code = generator.gen()
                return

    # ArrayDecl
    def visit_ArrayDecl(self, node):
        # Arrays in structs must specify value
        self.sizes.append(node.dim.value)
        self.visit(node.type)
        return

    # Pointer
    def visit_PtrDecl(self, node):
        self.sizes.append('ptr')
        self.ptr = True
        self.visit(node.type)
        return

    # Struct Type

    def visit_Struct(self, node):
        self.argtype = f'struct {node.name}'
        self.struct = True
        return

    # IdentifierType (Common and last node)

    def visit_IdentifierType(self, node):
        typ = node.names[0]
        if len(node.names):
            for t in node.names[1:]:
                typ += f' {t}'

        # Type is a typedef alias
        if typ in self.aliases.keys():
            typ, ptr = self.aliases[typ]

            # Typedefed pointer
            if ptr:
                self.sizes.append('ptr')
                self.ptr = True

            # Typedef struct
            if typ in self.structs.keys():
                typ = f'struct {typ}'
                self.struct = True

        self.argtype = typ
        return
