from pycparser.c_ast import (
    ID,
    Constant,
    Decl,
    ExprList,
    FuncCall,
    IdentifierType,
    TypeDecl,
)

from summboundverify.api import api_map

from ..default import DefaultGen


class PrimitiveTypeGen(DefaultGen):
    """Generate a symbolic variable of a primitive C type.

    The generated variable can optionally be initialized with a concrete
    value. When a maximum macro is configured, an upper-bound constraint
    can also be generated for the variable.
    """

    _max_id = 0

    def __init__(self, name, vartype, max_macro=None, max_args=None):
        super().__init__(name, vartype)
        self.max_macro = max_macro
        self.max_args = max_args or []

    def _limit_max(self, name):
        """Generate a declaration and upper-bound constraint for a variable."""

        PrimitiveTypeGen._max_id += 1

        max_name = f"max_{PrimitiveTypeGen._max_id}"
        max_macro = ID(self.max_macro)
        call = ID(api_map().assume)

        typ = IdentifierType(names=[self.vartype])
        type_decl = TypeDecl(max_name, [], None, typ)

        decl = Decl(max_name, [], [], [], [], type_decl, max_macro, None)

        le = FuncCall(ID("_ULE_"), ExprList([ID(name), ID(max_name)]))
        assume = FuncCall(call, ExprList([le]))

        return [decl, assume]

    def gen(self, const=None):
        """
        Generate the declaration of the primitive symbolic variable.

        If ``const`` is provided, the variable is initialized with that
        concrete value. Otherwise, it is initialized symbolically.

        If ``max_macro`` is configured, a maximum constraint is generated
        when ``max_args`` is empty or contains the variable name.
        """

        name = self.argname.name
        typ = IdentifierType(names=[self.vartype])

        type_decl = TypeDecl(name, [], None, typ)

        if const is not None:
            value = self.const_rvalue(const)
        else:
            value = self.symbolic_rvalue(Constant("string", f'"{name}"'))

        decl = Decl(name, [], [], [], [], type_decl, value, None)

        if (
            self.max_macro
            and (not self.max_args or name in self.max_args)
        ):
            return [decl, *self._limit_max(name)]

        return [decl]
