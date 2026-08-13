from pycparser.c_ast import Decl, ID, StructRef

from ..default import DefaultGen


class StructFieldGen(DefaultGen):
    """
    Generate initialization code for a struct field containing another struct.

    For example, for ``struct foo`` containing a ``bar`` field, produces
    code equivalent to:

        struct_foo_instance->bar = create_struct_bar(fuel);
    """

    def __init__(self, name, vartype, struct_name, field):
        super().__init__(name, vartype)

        self.struct_name = struct_name
        self.field = field

    def _field_lvalue(self):
        """Build the struct-field access.

        For ``struct_name="foo"`` and ``field="bar"``, produces:

            struct_foo_instance->bar
        """
        return StructRef(
            name=ID(f"struct_{self.struct_name}_instance"),
            type="->",
            field=ID(self.field),
        )

    def gen(self):
        """Generate initialization code for the nested struct field.

        For example:

            struct_foo_instance->bar = create_struct_bar(fuel);
        """
        lvalue = self._field_lvalue()
        rvalue = self.init_struct_rvalue(self.vartype)

        return [
            Decl(
                name=f"struct_{self.struct_name}_instance",
                quals=[], align=[], storage=[], funcspec=[],
                type=lvalue, init=rvalue, bitsize=None,
            )
        ]
