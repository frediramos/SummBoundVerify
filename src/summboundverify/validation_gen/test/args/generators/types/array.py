from pycparser.c_ast import ArrayRef, Assignment, BinaryOp, Compound, Constant, ID

from .....utils import terminate_string
from ..base_array import ArrayGen


class ArrayTypeGen(ArrayGen):
    """Generate a symbolic N-dimensional array.

    For example, a two-dimensional integer array produces code equivalent to:

        int array[rows][columns];

        for (int array_idx_1 = 0; array_idx_1 < rows; array_idx_1++)
            for (int array_idx_2 = 0; array_idx_2 < columns; array_idx_2++)
                array[array_idx_1][array_idx_2] =
                    sym_var_array("array", array_idx_2, sizeof(int) * 8);

    Struct-valued arrays initialize each element using the corresponding
    ``create_<struct>`` function instead.
    """

    def __init__(self, name, vartype, array, is_struct=False, null=None):
        super().__init__(name, vartype, array)

        self.is_struct = is_struct
        self.null = null

    def _array_lvalue(self):
        """Build the array element access for all dimensions.

        For a two-dimensional array named ``array``, produces:

            array[array_idx_1][array_idx_2]
        """
        lvalue = self.argname

        for dimension in range(1, self.dimension + 1):
            index = ID(f"{self.argname.name}_idx_{dimension}")
            lvalue = ArrayRef(lvalue, subscript=index)

        return lvalue

    def gen_array_init(self):
        """Generate the symbolic initialization of one array element.

        For a primitive array, produces code equivalent to:

            array[array_idx_1][array_idx_2] =
                sym_var_array("array", array_idx_2, sizeof(int) * 8);

        Struct elements are initialized using ``init_struct_rvalue``.
        """
        name = self.argname.name
        lvalue = self._array_lvalue()
        index = ID(f"{name}_idx_{self.dimension}")

        if self.is_struct:
            rvalue = self.init_struct_rvalue(self.vartype)
        else:
            rvalue = self.symbolic_rvalue_array(
                Constant("string", f'"{name}"'),
                index,
                self.vartype,
            )

        return Assignment(op="=", lvalue=lvalue, rvalue=rvalue)

    def gen(self, const=None, concrete=None):
        """Generate the array declaration and element initialization.

        When ``const`` is provided, only the corresponding declaration is
        generated.

        Otherwise, the array is declared and every element is initialized.

        For a one-dimensional character array, the generated array is
        terminated with a null byte. The same termination is performed when
        ``null`` is explicitly provided.

        If ``concrete`` is provided, selected elements are additionally
        initialized with concrete values.
        """

        # In declaration-only mode, skip array initialization.
        if const:
            return self.gen_array_decl(const)

        # Declare the array before generating the nested initialization loops.
        code: list = self.gen_array_decl()
        statement = Compound([self.gen_array_init()])

        # Build the innermost loop, corresponding to the last array dimension.
        index = f"{self.argname.name}_idx_{self.dimension}"
        loop = self.for_ast(index, self._size(self.sizes[-1]), statement)

        # Wrap the innermost loop with one loop for each remaining dimension.
        for dimension in range(self.dimension - 1, 0, -1):
            index = f"{self.argname.name}_idx_{dimension}"
            loop = self.for_ast(
                index,
                self._size(self.sizes[dimension - 1]),
                Compound([loop]),
            )

        code.append(loop)

        # Character arrays need a terminating null byte. An explicit ``null``
        # value can also request termination for other array types.
        if (self.vartype == "char" and self.dimension == 1) or self.null:
            if self.null:
                size = Constant("int", str(self.null))
            else:
                # Reserve the last element for the null terminator.
                size = BinaryOp(
                    "-",
                    self._size(self.sizes[-1]),
                    Constant("int", "1"),
                )

            code.append(terminate_string(self.argname, size))

            # Optionally overwrite selected elements with concrete values.
            if concrete:
                code.extend(self.fill_concrete(self.argname, concrete, size))

        return code
