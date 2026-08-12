import random

from pycparser.c_ast import (
    ID,
    For,
    Decl,
    PtrDecl,
    UnaryOp,
    ArrayRef,
    BinaryOp,
    Compound,
    Constant,
    DeclList,
    ExprList,
    FuncCall,
    TypeDecl,
    ArrayDecl,
    Assignment,
    IdentifierType,
)

from summboundverify.api import api_map
from summboundverify.validation_gen.utils import fill_array

from .default import DefaultGen


class ArrayGen(DefaultGen):
    """
    Generate declarations and initialization code for symbolic arrays.

    Supports both stack-allocated C arrays and heap-allocated arrays created
    through ``malloc``. Multi-dimensional heap arrays are represented as
    nested pointers, with one allocation loop for each dimension.

    For example, a two-dimensional array::

        int **array = malloc(sizeof(int *) * rows);

        for (int i = 0; i < rows; i++)
            array[i] = malloc(sizeof(int) * columns);
    """

    def __init__(self, name, vartype, array):
        super().__init__(name, vartype)

        self.sizes = array
        self.dimension = len(array)

    def _size(self, value: str):
        """
        Convert an array size into a C AST expression.

        Numeric sizes are represented as integer constants. Named sizes are
        resolved through ``size_macros`` when available; otherwise they are
        represented as C identifiers.
        """
        if value.isnumeric():
            return Constant("int", value)

        return self.size_macros.get(value, ID(value))

    def declare_stack_array(self, const=None):
        """
        Generate a stack-allocated N-dimensional array declaration.

        For example, an array with sizes ``[10, 5]`` produces::

            int array[10][5];

        ``const`` is passed directly to the generated ``Decl`` node.
        """
        name = self.argname.name
        typedecl = TypeDecl(name, [], None, IdentifierType([self.vartype]))

        array = ArrayDecl(typedecl, self._size(self.sizes[-1]), [])

        for size in reversed(self.sizes[:-1]):
            array = ArrayDecl(array, self._size(size), [])

        return [Decl(name, [], [], [], [], array, const, None)]

    def declare_heap_array(self):
        """
        Generate a heap-allocated N-dimensional array.

        The first dimension is allocated when the array is declared. For
        additional dimensions, nested ``for`` loops allocate each sub-array.

        For example, a two-dimensional ``int`` array produces code equivalent
        to::

            int **array = malloc(sizeof(int *) * rows);

            for (int malloc_idx_1 = 0; malloc_idx_1 < rows; malloc_idx_1++)
                array[malloc_idx_1] =
                    malloc(sizeof(int) * columns);

        The generated AST uses ``malloc_idx_N`` as the loop variable for
        dimension ``N``.
        """
        name = self.argname.name

        typedecl = TypeDecl(name, [], None, IdentifierType([self.vartype]))
        typtr = PtrDecl(
            [],
            TypeDecl(name, [], None, IdentifierType([self.vartype])),
        )

        for _ in range(1, self.dimension - 1):
            typtr = PtrDecl([], typtr)

        sizeof = FuncCall(ID("sizeof"), ExprList([typtr]))
        size = BinaryOp("*", sizeof, self._size(self.sizes[0]))
        rvalue = FuncCall(ID("malloc"), ExprList([size]))

        arrptr = PtrDecl([], typedecl)
        for _ in range(1, self.dimension):
            arrptr = PtrDecl([], arrptr)

        code: list = [Decl(name, [], [], [], [], arrptr, rvalue, None)]

        if self.dimension == 1:
            return code

        # Allocate the innermost dimension.
        typtr = IdentifierType([self.vartype])
        sizeof = FuncCall(ID("sizeof"), ExprList([typtr]))

        index = "malloc_idx_1"
        arrayref = ArrayRef(ID(name), ID(index))

        for i in range(2, self.dimension):
            index = f"malloc_idx_{i}"
            arrayref = ArrayRef(arrayref, ID(index))

        size = BinaryOp("*", sizeof, self._size(self.sizes[-1]))
        stmt = Assignment(
            "=",
            arrayref,
            FuncCall(ID("malloc"), ExprList([size])),
        )

        decls = self.for_ast(
            index,
            self._size(self.sizes[-2]),
            Compound([stmt]),
        )

        # Each outer dimension points to an array of the type constructed
        # for the dimension immediately inside it.
        typtr = PtrDecl([], TypeDecl(name, [], None, typtr))

        for i in range(self.dimension - 2, 0, -1):
            index = "malloc_idx_1"
            arrayref = ArrayRef(ID(name), ID(index))

            for j in range(2, i + 1):
                index = f"malloc_idx_{j}"
                arrayref = ArrayRef(arrayref, ID(index))

            sizeof = FuncCall(ID("sizeof"), ExprList([typtr]))
            size = BinaryOp("*", sizeof, self._size(self.sizes[i]))

            stmt = Assignment(
                "=",
                arrayref,
                FuncCall(ID("malloc"), ExprList([size])),
            )

            decls = self.for_ast(
                index,
                self._size(self.sizes[i - 1]),
                Compound([stmt, decls]),
            )

            typtr = PtrDecl([], typtr)

        code.append(decls)
        return code

    def gen_array_decl(self, const=None):
        """
        Generate the appropriate array declaration.

        Without ``const``, a stack-allocated array is generated. Otherwise,
        the array is represented as a pointer declaration initialized with
        the provided constant value.

        The special ``&`` value indicates that the generated declaration
        represents a pointer to the array rather than the array itself.
        """

        if const is None:
            return self.declare_stack_array()

        if const == "&":
            self.dimension -= 1
            rvalue = None
        else:
            rvalue = self.const_rvalue(const)

        name = self.argname.name
        typedecl = TypeDecl(name, [], None, IdentifierType([self.vartype]))

        ptr = PtrDecl([], typedecl)

        for _ in range(1, self.dimension):
            ptr = PtrDecl([], ptr)

        return [Decl(name, [], [], [], [], ptr, rvalue, None)]

    def for_ast(self, index, size, stmt):
        """Create a C ``for`` loop over an array dimension.

        The generated loop has the form::

            for (int index = 0; index < size; index++)
                stmt;
        """
        typedecl = TypeDecl(index, [], None, IdentifierType(["int"]))
        zero = Constant("int", "0")
        decl = Decl(index, [], [], [], [], typedecl, zero, None)
        init = DeclList(decls=[decl])

        cond = BinaryOp("<", ID(index), size)
        nxt = UnaryOp("p++", ID(index))

        return For(init, cond, nxt, stmt)

    def symbolic_rvalue_array(self, name, index, vartype):
        """
        Generate an expression for a symbolic array element.

        The generated call invokes ``sym_var_array`` with the array name,
        element index, and element size in bits.

        The element size is calculated as::

            sizeof(vartype) * 8
        """
        call = ID(api_map().sym_var_array)

        sizeof = FuncCall(ID("sizeof"), ExprList([ID(vartype)]))
        size = BinaryOp("*", sizeof, Constant("int", "8"))

        return FuncCall(call, ExprList([name, index, size]))

    def fill_concrete(self, lvalue, const, size):
        """
        Generate statements that initialize concrete array elements.

        If ``const`` is a string, its first character determines how many
        elements are initialized at pseudo-random indices. If ``const`` is a
        list, its values are interpreted as explicit element indices.

        All initialized elements receive the character value ``'1'``.
        """
        char = Constant("char", "'1'")

        if isinstance(const, str):
            count = int(const[0])

            return [
                fill_array(
                    lvalue,
                    char,
                    BinaryOp(
                        "%",
                        Constant("int", str(random.randint(10, 20))),
                        size,
                    ),
                )
                for _ in range(count)
            ]

        if isinstance(const, list):
            return [
                fill_array(lvalue, char, Constant("int", str(index)))
                for index in const
            ]

        return []
