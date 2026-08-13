from pycparser.c_ast import Decl, ExprList, FuncCall, ID, IdentifierType, TypeDecl

from ..default import DefaultGen


class StructTypeGen(DefaultGen):
    """Generate a symbolic struct variable.

    For example, for ``name="x"`` and ``vartype="struct foo"``, generates:

        struct foo x = create_struct_foo(fuel);
    """

    def gen(self):
        """Generate the declaration of the symbolic struct variable.

        The struct is initialized by calling its corresponding
        ``create_<struct>`` function with the current fuel value.
        """
        name = self.argname.name
        struct_type = self.vartype.replace(" ", "_")

        # Declare the variable using its struct type.
        type_decl = TypeDecl(
            name, [], None, IdentifierType(names=[self.vartype])
        )

        # Initialize it using the generated struct constructor.
        rvalue = FuncCall(
            ID(f"create_{struct_type}"),
            ExprList([self.fuel]),
        )

        return [Decl(name, [], [], [], [], type_decl, rvalue, None)]
