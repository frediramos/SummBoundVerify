from pycparser.c_ast import Decl, ID, StructRef

from ..default import DefaultGen


class StructFieldGen(DefaultGen):
    """
    Generate initialization code for a struct field containing another struct.

    For example, for ``struct foo`` containing a ``bar`` field, produces
    code equivalent to:

        struct_foo_instance->bar = create_struct_bar(fuel);
    """

    def __init__(self, name, vartype, struct_name, field):
        super().__init__(name, vartype)

        self.struct_name = struct_name
        self.field = field

    def gen(self):
        # struct->field = create_struct(fuel)
        code = []
        name = f'struct_{self.struct_name}_instance'

        # Declare Variable
        lvalue = StructRef(
            name=ID(f'{name}'),
            type='->',
            field=ID(f'{self.field}')
        )

        rvalue = self.init_struct_rvalue(self.vartype)
        decl = Decl(name, [], [], [], [], lvalue, rvalue, None)
        code.append(decl)

        return code
