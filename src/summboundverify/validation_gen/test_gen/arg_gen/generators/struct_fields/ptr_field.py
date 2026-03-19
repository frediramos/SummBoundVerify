from pycparser.c_ast import *

from ..base_array import ArrayGen


# N-dimension pointer struct field
class PtrFieldGen(ArrayGen):
    def __init__(self, name, vartype, struct_name, field, sizes, struct=False):
        super().__init__(name, vartype, sizes)

        self.struct_name = struct_name
        self.field = field
        self.struct = struct

    def recursiveStruct(self, name, lvalue, ptr, fname):
        code = []

        cond = BinaryOp(op='>', left=ID('fuel'), right=Constant('int', str(0)))

        fuel = BinaryOp(op='-', left=ID('fuel'), right=Constant('int', str(1)))
        rvalue = FuncCall(ID(f'create_{fname}'), ExprList([fuel]))
        ifdecl = Decl(name, [], [], [], [], lvalue, rvalue, None)

        elsedecl = Decl(name, [], [], [], [], ptr, ID('NULL'), None)

        iffuel = If(cond, Compound([ifdecl]), Compound([elsedecl]))

        code.append(iffuel)
        return code

    # struct->ptr[i][j] = symbolic();

    def gen_ptr_init(self):
        name = self.argname.name

        # array[index]
        index = f'{name}_index_1'
        lvalue = ArrayRef(self.argname, subscript=ID(index))

        # Loop for N array dimensions array[][]...
        for i in range(2, self.dimension+1):

            index = f'{name}_index_{i}'
            lvalue = ArrayRef(lvalue, subscript=ID(index))

        # struct_instance->Array[i][j]
        sname = f'struct_{self.struct_name}_instance'
        lvalue = StructRef(name=ID(f'{sname}'), type='->', field=lvalue)

        ptr = StructRef(name=ID(f'{sname}'), type='->', field=self.argname)

        fname = self.vartype.replace(' ', '_')

        # Return assignment
        if self.struct:

            # Recursive struct
            if f'struct_{self.struct_name}' == fname:
                return self.recursiveStruct(name, lvalue, ptr, fname)

            # Other struct
            else:
                rvalue = self.init_struct_rvalue(self.vartype)
        else:
            rvalue = self.symbolic_rvalue(
                Constant('string', f'\"{self.field}\"'))

        return [Assignment(op='=', lvalue=lvalue, rvalue=rvalue)]

    # Fill array field

    def gen(self):
        code = []
        name = self.argname.name

        code += self.declare_heap_array()

        stmt = Compound(self.gen_ptr_init())
        sizes = self.sizes

        index = f'{name}_index_{self.dimension}'
        for_ast_code = self.For_ast(index, self._size(sizes.pop(0)), stmt)

        for i in range(self.dimension-1, 0, -1):
            index = f'{name}_index_{i}'
            for_ast_code = self.For_ast(index, self._size(
                sizes.pop(0)), Compound([for_ast_code]))

        code.append(for_ast_code)
        return code
