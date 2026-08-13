from pycparser.c_ast import (
    ArrayRef,
    Assignment,
    Compound,
    Constant,
    ID,
    StructRef,
)

from ..base_array import ArrayGen


class ArrayFieldGen(ArrayGen):
    """
    Generate initialization code for an N-dimensional array struct field.

    For example, for a two-dimensional field ``array`` in ``struct foo``,
    the generated assignment is equivalent to:

        struct_foo_instance->array[array_idx_1][array_idx_2] = new_sym_var("array");

    The generator also creates the nested loops required to visit every
    element of the array.
    """

    def __init__(
        self,
        name,
        vartype,
        struct_name,
        field,
        sizes,
        is_struct=False,
    ):
        super().__init__(name, vartype, sizes)

        self.struct_name = struct_name
        self.field = field
        self.is_struct = is_struct

    def _array_lvalue(self):
        """Build the array element access for all dimensions.

        For a two-dimensional array named ``array``, produces the
        equivalent of:

            array[array_idx_1][array_idx_2]

        For a three-dimensional array, this becomes:

            array[array_idx_1][array_idx_2][array_idx_3]
        """
        lvalue = self.argname

        for dimension in range(1, self.dimension + 1):
            index = ID(f"{self.argname.name}_idx_{dimension}")
            lvalue = ArrayRef(lvalue, subscript=index)

        return lvalue

    def _struct_field_lvalue(self, array_lvalue):
        """Build the struct-field access containing the array.

        Given:

            array[array_idx_1][array_idx_2]

        produces the equivalent of:

            struct_foo_instance->array[array_idx_1][array_idx_2]
        """
        instance = ID(f"struct_{self.struct_name}_instance")

        return StructRef(
            name=instance,
            type="->",
            field=array_lvalue,
        )

    def _rvalue(self):
        """Build the value assigned to the array element.

        For a primitive element, produces a symbolic value equivalent to:

            new_sym_var("array")

        For a struct element, initializes a symbolic struct value instead.
        """
        if self.is_struct:
            return self.init_struct_rvalue(self.vartype)

        return self.symbolic_rvalue(
            Constant("string", f'"{self.field}"')
        )

    def gen_array_init(self):
        """Generate the assignment for one array element.

        For example, for a two-dimensional primitive array, generates
        an assignment equivalent to:

            struct_foo_instance->array[array_idx_1][array_idx_2]
                = new_sym_var("array");
        """
        lvalue = self._struct_field_lvalue(
            self._array_lvalue()
        )

        return [
            Assignment(
                op="=",
                lvalue=lvalue,
                rvalue=self._rvalue(),
            )
        ]

    def gen(self):
        """Generate nested loops that initialize every array element.

        For example, for an array ``array[2][3]``, generates code
        equivalent to:

            for (array_idx_2 = 0; array_idx_2 < 3; array_idx_2++) {
                for (array_idx_1 = 0; array_idx_1 < 2; array_idx_1++) {
                    struct_foo_instance->array[array_idx_1][array_idx_2]
                        = new_sym_var("array");
                }
            }
        """
        sizes = list(self.sizes)
        statement = Compound(self.gen_array_init())

        loop = statement

        for dimension in range(self.dimension, 0, -1):
            index = ID(f"{self.argname.name}_idx_{dimension}")
            size = self._size(sizes[dimension - 1])

            loop = self.for_ast(
                index,
                size,
                loop if isinstance(loop, Compound) else Compound([loop]),
            )

        return [loop]
