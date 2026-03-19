from pycparser.c_ast import *
from ..default import DefaultGen

MAX_ID = 0

# Create a primitive symbolic var


class PrimitiveTypeGen(DefaultGen):
    def __init__(self, name, vartype, max_macro=None, max_args=[]):
        super().__init__(name, vartype)

        self.max_macro = max_macro
        self.max_args = max_args

    # size_t max = MAX_NUM_1;
    # assume(_ULE_(&n, &max, sizeof(size_t) * 8));

    def _limit_max(self, name):
        global MAX_ID
        MAX_ID += 1

        max_name = f'max_{MAX_ID}'
        lvalue = TypeDecl(max_name, [], None,
                          IdentifierType(names=[self.vartype]))
        rvalue = ID(self.max_macro)
        decl = Decl(max_name, [], [], [], [], lvalue, rvalue, None)

        max = ID(max_name)
        value = ID(name)
        # size = self.type_size(self.vartype)

        le = FuncCall(ID('_ULE_'), ExprList([value, max]))
        assume = FuncCall(ID('assume'), ExprList([le]))

        return [decl, assume]

    # e.g, int a = summ_new_sym_var(sizeof(int))

    def gen(self, const=None):

        code = []
        name = self.argname.name

        # Declare Variable
        lvalue = TypeDecl(name, [], None, IdentifierType(names=[self.vartype]))

        # Make symbolic type
        if const is not None:
            rvalue = self.const_rvalue(const)
        else:
            rvalue = self.symbolic_rvalue(Constant('string', f'\"{name}\"'))

        # Assemble declaration
        decl = Decl(name, [], [], [], [], lvalue, rvalue, None)
        code.append(decl)

        if (self.max_macro and const is None)\
                and (name in self.max_args or not self.max_args):
            code += self._limit_max(name)
        return code
