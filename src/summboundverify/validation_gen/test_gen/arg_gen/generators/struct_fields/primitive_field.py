from pycparser.c_ast import Assignment, Constant, ID, StructRef

from ..default import DefaultGen


class PrimitiveFieldGen(DefaultGen):
    """
    Generate initialization code for a primitive struct field.

    For example, given ``struct_name="foo"`` and ``field="x"``,
    generates an assignment equivalent to:

        struct_foo_instance->x = new_sym_var("x");
    """

    def __init__(self, name, vartype, struct_name, field):
        super().__init__(name, vartype)

        self.struct_name = struct_name
        self.field = field

    def _field_lvalue(self):
        """Build the struct-field access.

        For ``struct_name="foo"`` and ``field="x"``, produces the
        equivalent of:

            struct_foo_instance->x
        """
        return StructRef(
            name=ID(f"struct_{self.struct_name}_instance"),
            type="->",
            field=ID(self.field),
        )

    def _rvalue(self):
        """Build the symbolic value assigned to the field.

        For ``field="x"``, produces the equivalent of:

            new_sym_var("x")
        """
        return self.symbolic_rvalue(
            Constant("string", f'"{self.field}"')
        )

    def gen(self):
        """Generate the assignment to the struct field.

        Example:

            struct_foo_instance->x = new_sym_var("x");
        """
        return [
            Assignment(
                op="=",
                lvalue=self._field_lvalue(),
                rvalue=self._rvalue(),
            )
        ]
