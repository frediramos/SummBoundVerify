from pycparser.c_ast import BinaryOp, Constant, ExprList, FuncCall, ID, NodeVisitor

from summboundverify.api import api_map
from summboundverify.validation_gen.utils import (
    ARRAY_SIZE_MACRO,
    FUEL_MACRO,
    POINTER_SIZE_MACRO,
)


class DefaultGen(NodeVisitor):
    """Base generator providing common AST construction helpers.

    Generators derived from this class use these helpers to construct
    symbolic values, struct values, sizes, and constants.
    """

    def __init__(self, name, vartype):
        super().__init__()

        self.argname = name  # ID node
        self.vartype = vartype  # C type name

        self.size_macros = {
            "array": ID(ARRAY_SIZE_MACRO),
            "ptr": ID(POINTER_SIZE_MACRO),
        }

        self.fuel = ID(FUEL_MACRO)

    def init_struct_rvalue(self, vartype):
        """Build a call that initializes a symbolic struct value.

        For example, for ``vartype="struct foo"``, produces:

            create_struct_foo(fuel)
        """
        struct_type = vartype.replace(" ", "_")

        return FuncCall(
            name=ID(f"create_{struct_type}"),
            args=ExprList([self.fuel]),
        )

    def type_size(self, vartype):
        """Build an expression computing the size of a C type in bits.

        For example, for ``vartype="int"``, produces an expression
        equivalent to:

            sizeof(int) * 8
        """
        return BinaryOp(
            op="*",
            left=FuncCall(
                name=ID("sizeof"),
                args=ExprList([ID(vartype)]),
            ),
            right=Constant("int", "8"),
        )

    def symbolic_rvalue(self, name):
        """Build a call that creates a named symbolic value.

        For example, with ``name="x"`` and ``vartype="int"``, produces:

            __sym_var_named("x", sizeof(int) * 8)
        """
        call = ID(api_map().sym_var_named)
        args = ExprList([name, self.type_size(self.vartype)])

        return FuncCall(name=call, args=args)

    def const_rvalue(self, const):
        """Convert a Python constant to the corresponding C AST node.

        Examples:

            42     -> 42
            "x"    -> 'x'
            "foo"  -> "foo"

        Returns ``None`` for unsupported values.
        """
        if isinstance(const, int):
            return Constant("int", str(const))

        if isinstance(const, str):
            if len(const) == 1:
                return Constant("char", const)

            if len(const) > 1:
                return Constant("string", const)

        return None
