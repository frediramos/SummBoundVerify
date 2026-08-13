from pycparser.c_ast import (
    ArrayRef, Assignment, BinaryOp, Compound, Constant, Decl, ExprList,
    FuncCall, ID, If, StructRef,
)

from ..base_array import ArrayGen


class PtrFieldGen(ArrayGen):
    """
    Generate initialization code for an N-dimensional pointer struct field.

    For example, for a two-dimensional ``ptr`` field:

        struct_foo_instance->ptr[i][j] = new_sym_var("ptr");

    Recursive struct pointers are initialized using a fuel parameter:

        if (fuel > 0) {
            struct_foo_instance->ptr[i][j] = create_struct_foo(fuel - 1);
        } else {
            struct_foo_instance->ptr[i][j] = NULL;
        }
    """

    def __init__(self, name, vartype, struct_name, field, sizes, is_struct=False):
        super().__init__(name, vartype, sizes)

        self.struct_name = struct_name
        self.field = field
        self.is_struct = is_struct

    def _recursive_struct_init(self, name, lvalue, ptr, struct_type):
        """Generate fuel-bounded initialization for a recursive struct.

        Produces code equivalent to:

            if (fuel > 0)
                ptr = create_struct_foo(fuel - 1);
            else
                ptr = NULL;
        """
        condition = BinaryOp(
            op=">", left=ID("fuel"), right=Constant("int", "0")
        )
        fuel = BinaryOp(
            op="-", left=ID("fuel"), right=Constant("int", "1")
        )

        call = FuncCall(ID(f"create_{struct_type}"), ExprList([fuel]))

        recursive_init = Decl(
            name=name, quals=[], align=[], storage=[], funcspec=[],
            type=lvalue, init=call, bitsize=None,
        )
        null_init = Decl(
            name=name, quals=[], align=[], storage=[], funcspec=[],
            type=ptr, init=ID("NULL"), bitsize=None,
        )

        return [If(condition, Compound([recursive_init]), Compound([null_init]))]

    def _array_lvalue(self):
        """Build the array element access for all dimensions.

        For ``ptr`` with two dimensions, produces:

            ptr[ptr_index_1][ptr_index_2]
        """
        lvalue = self.argname

        for dimension in range(1, self.dimension + 1):
            index = ID(f"{self.argname.name}_index_{dimension}")
            lvalue = ArrayRef(lvalue, subscript=index)

        return lvalue

    def _struct_field_lvalue(self, field):
        """Build access to a field of the struct instance.

        For ``ptr`` in ``struct foo``, produces:

            struct_foo_instance->ptr
        """
        return StructRef(
            name=ID(f"struct_{self.struct_name}_instance"),
            type="->",
            field=field,
        )

    def _rvalue(self):
        """Build the value assigned to a pointer element.

        A primitive element produces:

            new_sym_var("ptr")

        while a struct element is initialized using ``init_struct_rvalue``.
        """
        if self.is_struct:
            return self.init_struct_rvalue(self.vartype)

        return self.symbolic_rvalue(Constant("string", f'"{self.field}"'))

    def gen_ptr_init(self):
        """Generate initialization code for one pointer-array element.

        For example:

            struct_foo_instance->ptr[i][j] = new_sym_var("ptr");
        """
        lvalue = self._struct_field_lvalue(self._array_lvalue())
        ptr = self._struct_field_lvalue(self.argname)
        struct_type = self.vartype.replace(" ", "_")

        if self.is_struct:
            if f"struct_{self.struct_name}" == struct_type:
                return self._recursive_struct_init(
                    self.argname.name, lvalue, ptr, struct_type
                )

            rvalue = self.init_struct_rvalue(self.vartype)
        else:
            rvalue = self._rvalue()

        return [Assignment(op="=", lvalue=lvalue, rvalue=rvalue)]

    def gen(self):
        """Generate heap allocation and nested initialization loops.

        For a ``ptr[2][3]`` field, produces code equivalent to:

            for (ptr_index_2 = 0; ptr_index_2 < 3; ptr_index_2++) {
                for (ptr_index_1 = 0; ptr_index_1 < 2; ptr_index_1++) {
                    struct_foo_instance->ptr[ptr_index_1][ptr_index_2] =
                        new_sym_var("ptr");
                }
            }
        """
        sizes = list(self.sizes)
        code = self.declare_heap_array()
        loop = Compound(self.gen_ptr_init())

        for dimension in range(self.dimension, 0, -1):
            index = ID(f"{self.argname.name}_index_{dimension}")
            size = self._size(sizes[dimension - 1])
            loop = self.for_ast(index, size, loop)

        code.append(loop)
        return code
