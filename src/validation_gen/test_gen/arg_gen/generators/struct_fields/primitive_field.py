from pycparser.c_ast import *

from ..default import DefaultGen


# Primitive type struct field
class PrimitiveFieldGen(DefaultGen):
    def __init__(self, name, vartype, struct_name, field):
        super().__init__(name, vartype)

        self.struct_name = struct_name
        self.field = field

    # e.g: struct->field = new_sym_var(32)
    def gen(self):
        code = []
        name = f'struct_{self.struct_name}_instance'

        # Make symbolic type
        rvalue = self.symbolic_rvalue(Constant('string', f'\"{self.field}\"'))

        # struct->field
        lvalue = StructRef(name=ID(f'{name}'),
                           type='->', field=ID(f'{self.field}'))

        # Assemble declaration
        decl = Decl(name, [], [], [], [], lvalue, rvalue, None)

        code.append(decl)

        return code
