from pycparser.c_ast import (
    Constant,
    Decl,
    ExprList,
    FuncCall,
    ID,
    IdentifierType,
    TypeDecl,
)

from summboundverify.api import api_map

from ..default import DefaultGen


class PrimitiveTypeGen(DefaultGen):
    """Generate a symbolic variable of a primitive C type.

    For example, for ``name="x"`` and ``vartype="int"``, generates:

        int x = sym_var_named("x", sizeof(int) * 8);

    A concrete value can be provided instead:

        int x = 42;

    When ``max_macro`` is configured, an upper-bound constraint can also
    be generated:

        int max_1 = MAX_VALUE;
        __assume(_ULE_(x, max_1));
    """

    _max_id = 0

    def __init__(self, name, vartype, max_macro=None, max_args=None):
        super().__init__(name, vartype)
        self.max_macro = max_macro
        self.max_args = max_args or []

    def _limit_max(self, name):
        """Generate a maximum-value declaration and constraint.

        For example, generates code equivalent to:

            int max_1 = MAX_VALUE;
            __assume(_ULE_(x, max_1));
        """
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
        """Generate the declaration of the primitive symbolic variable.

        If ``const`` is provided, initializes the variable with that
        concrete value. Otherwise, initializes it symbolically.

        If ``max_macro`` is configured, generates an upper-bound constraint
        when ``max_args`` is empty or contains the variable name.
        """
        name = self.argname.name
        typ = IdentifierType(names=[self.vartype])
        type_decl = TypeDecl(name, [], None, typ)

        # Use a concrete initializer when requested; otherwise create a
        # symbolic value associated with the variable's name.
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
