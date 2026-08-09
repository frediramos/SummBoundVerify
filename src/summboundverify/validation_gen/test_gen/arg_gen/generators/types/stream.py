from pycparser.c_ast import (
    ID,
    Decl,
    PtrDecl,
    Constant,
    ExprList,
    FuncCall,
    TypeDecl,
    IdentifierType,
)

from ..default import DefaultGen

# Pointer arguments that name a stream rather than an array of elements.
#
# The array generator would emit `sizeof(FILE)` for these, which does not
# compile: FILE is opaque by design and its size is not a caller's business.
# They are drawn as a real stream over fresh bytes instead -- see
# sym_var_stream in the concrete runtime.
STREAM_TYPES = frozenset({'FILE'})


class StreamTypeGen(DefaultGen):
    """Build a readable stream argument from fresh input bytes.

    Fuzz-only: the concrete runtime backs this with fmemopen, and there is no
    symbolic counterpart, so `validation_tool.se_support` routes these targets
    away from symbolic execution.
    """

    def __init__(self, name, vartype, length):
        super().__init__(name, vartype)
        self.length = length

    # FILE *f = sym_var_stream("f", ARRAY_SIZE_1);
    def gen(self, const=None):
        name = self.argname.name

        lvalue = PtrDecl([], TypeDecl(
            name, [], None, IdentifierType(names=[self.vartype])
        ))

        args = ExprList([
            Constant('string', f'"{name}"'),
            ID(self.length),
        ])
        rvalue = FuncCall(ID('sym_var_stream'), args)

        return [Decl(name, [], [], [], [], lvalue, rvalue, None)]
