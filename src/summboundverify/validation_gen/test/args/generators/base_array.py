import random

from pycparser.c_ast import (
    ArrayDecl,
    ArrayRef,
    Assignment,
    BinaryOp,
    Compound,
    Constant,
    Decl,
    DeclList,
    ExprList,
    For,
    FuncCall,
    ID,
    IdentifierType,
    PtrDecl,
    TypeDecl,
    UnaryOp,
)

from summboundverify.api import api_map
from summboundverify.validation_gen.utils import fill_array

from .default import DefaultGen


class ArrayGen(DefaultGen):
    """Generate declarations and initialization code for symbolic arrays.

    Supports both stack-allocated C arrays and heap-allocated arrays created
    through ``malloc``.

    A two-dimensional stack array produces:

        int array[rows][columns];

    A two-dimensional heap array produces:

        int **array = malloc(sizeof(int *) * rows);

        for (int malloc_idx_1 = 0; malloc_idx_1 < rows; malloc_idx_1++)
            array[malloc_idx_1] = malloc(sizeof(int) * columns);
    """

    def __init__(self, name, vartype, array):
        super().__init__(name, vartype)

        self.sizes = array
        self.dimension = len(array)

    def _size(self, value: str):
        """Convert an array size into a C AST expression.

        Numeric sizes produce integer constants. Named sizes are resolved
        through ``size_macros`` when available.

        For example:

            "10"         -> 10
            "array"      -> ARRAY_SIZE_MACRO
            "my_size"    -> my_size
        """
        if value.isnumeric():
            return Constant("int", value)

        return self.size_macros.get(value, ID(value))

    def declare_stack_array(self, const=None):
        """Generate a stack-allocated N-dimensional array declaration.

        For sizes ``[10, 5]``, produces:

            int array[10][5];
        """
        name = self.argname.name
        typedecl = TypeDecl(name, [], None, IdentifierType([self.vartype]))

        array = ArrayDecl(typedecl, self._size(self.sizes[-1]), [])

        for size in reversed(self.sizes[:-1]):
            array = ArrayDecl(array, self._size(size), [])

        return [Decl(name, [], [], [], [], array, const, None)]

    def declare_heap_array(self):
        """Generate a heap-allocated N-dimensional array.

        For ``int array[rows][columns]``, produces:

            int **array = malloc(sizeof(int *) * rows);

            for (int malloc_idx_1 = 0; malloc_idx_1 < rows; malloc_idx_1++)
                array[malloc_idx_1] = malloc(sizeof(int) * columns);
        """
        name = self.argname.name

        typedecl = TypeDecl(name, [], None, IdentifierType([self.vartype]))
        typtr = PtrDecl([], typedecl)

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

        for dimension in range(2, self.dimension):
            index = f"malloc_idx_{dimension}"
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
            Compound([stmt])
        )

        # Allocate each outer dimension.
        typtr = PtrDecl([], TypeDecl(name, [], None, typtr))

        for dimension in range(self.dimension - 2, 0, -1):
            index = "malloc_idx_1"
            arrayref = ArrayRef(ID(name), ID(index))

            for inner in range(2, dimension + 1):
                index = f"malloc_idx_{inner}"
                arrayref = ArrayRef(arrayref, ID(index))

            sizeof = FuncCall(ID("sizeof"), ExprList([typtr]))
            size = BinaryOp("*", sizeof, self._size(self.sizes[dimension]))

            stmt = Assignment(
                "=",
                arrayref,
                FuncCall(ID("malloc"), ExprList([size])),
            )

            decls = self.for_ast(
                index,
                self._size(self.sizes[dimension - 1]),
                Compound([stmt, decls]),
            )

            typtr = PtrDecl([], typtr)

        code.append(decls)
        return code

    def gen_array_decl(self, const=None):
        """Generate an array or pointer declaration.

        With no constant, produces a stack-allocated array:

            int array[10][5];

        With a constant, produces a pointer declaration initialized with
        that value.

        The special ``&`` value does not initialize the array and removes a '*' level.
        """
        if const is None:
            return self.declare_stack_array()

        if const == "&":
            dimension = self.dimension - 1
            rvalue = None
        else:
            dimension = self.dimension
            rvalue = self.const_rvalue(const)

        name = self.argname.name
        typedecl = TypeDecl(name, [], None, IdentifierType([self.vartype]))
        ptr = PtrDecl([], typedecl)

        for _ in range(1, dimension):
            ptr = PtrDecl([], ptr)

        return [Decl(name, [], [], [], [], ptr, rvalue, None)]

    def for_ast(self, index, size, stmt):
        """Create a C ``for`` loop over an array dimension.

        Produces:

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
        """Generate a symbolic array-element expression.

        Produces a call equivalent to:

            sym_var_array(name, index, sizeof(vartype) * 8);
        """
        call = ID(api_map().sym_var_array)
        sizeof = FuncCall(ID("sizeof"), ExprList([ID(vartype)]))
        size = BinaryOp("*", sizeof, Constant("int", "8"))

        return FuncCall(call, ExprList([name, index, size]))

    def fill_concrete(self, lvalue, const, size):
        """Generate statements that initialize concrete array elements.

        A string uses its first character as the number of elements to fill
        at random indices. A list specifies the indices explicitly.

        Every selected element receives ``'1'``.

        For example, ``const=[0, 2, 5]`` produces assignments equivalent to:

            array[0] = '1';
            array[2] = '1';
            array[5] = '1';
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
