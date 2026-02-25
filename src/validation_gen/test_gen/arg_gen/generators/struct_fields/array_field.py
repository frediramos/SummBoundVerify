from pycparser.c_ast import *

from ..base_array import ArrayGen


# N-dimension array struct field
class ArrayFieldGen(ArrayGen):
    def __init__(self, name, vartype, struct_name, field, sizes, struct=False):
        super().__init__(name, vartype, sizes)

        self.struct_name = struct_name
        self.field = field
        self.struct = struct

    # struct->Array[i][j] = symbolic();

    def gen_array_init(self):
        name = self.argname.name

        # array[index]
        index = f'{name}_idx_1'
        lvalue = ArrayRef(self.argname, subscript=ID(index))

        # Loop for N array dimensions array[][]...
        for i in range(2, self.dimension+1):

            index = f'{name}_idx_{i}'
            lvalue = ArrayRef(lvalue, subscript=ID(index))

        # struct_instance->Array[i][j]
        sname = f'struct_{self.struct_name}_instance'
        lvalue = StructRef(name=ID(f'{sname}'), type='->', field=lvalue)

        fname = self.vartype.replace(' ', '_')

        # Return assignment
        if self.struct:

            rvalue = self.init_struct_rvalue(self.vartype)
        else:
            rvalue = self.symbolic_rvalue(
                Constant('string', f'\"{self.field}\"'))

        return [Assignment(op='=', lvalue=lvalue, rvalue=rvalue)]

    # Fill array field

    def gen(self):
        code = []
        name = self.argname.name

        stmt = Compound(self.gen_array_init())
        sizes = self.sizes

        index = f'{name}_idx_{self.dimension}'
        for_ast_code = self.For_ast(index, self._size(sizes.pop(0)), stmt)

        for i in range(self.dimension-1, 0, -1):
            index = f'{name}_idx_{i}'
            for_ast_code = self.For_ast(index, self._size(
                sizes.pop(0)), Compound([for_ast_code]))

        code.append(for_ast_code)
        return code
