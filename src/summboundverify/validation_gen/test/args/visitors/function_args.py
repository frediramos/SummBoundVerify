from pycparser.c_ast import (
    ID,
    Decl,
    Struct,
    PtrDecl,
    TypeDecl,
    ArrayDecl,
    FuncDecl,
    IdentifierType,
    NodeVisitor
)

from ..generators.types import ArrayTypeGen, PrimitiveTypeGen, StructTypeGen


class ArgVisitor(NodeVisitor):
    def __init__(
        self,
        size_macro: str | None = None,
        max_macro=None,
        null=None,
        max_args: list | None = None,
        default=None,
        concrete_arr: list | None = None,
    ) -> None:
        # Store argument node (Decl)
        self.node: Decl | None = None

        # Array or pointer
        self.size_macro = size_macro or "ptr"
        self.null = null
        self.max_macro = max_macro
        self.max_args = max_args or []
        self.default = default
        self.concrete_arr = concrete_arr or []

        # Argument information
        self.argname: str | None = None
        self.argtype: str | None = None

        # Array properties
        self.array_dim: list[str] = []

        # Struct properties
        self.struct: bool = False

        # Generated declarations
        self.code: list[Decl] = []

    def get_type(self) -> tuple[str, list[str], bool]:
        assert self.argtype is not None
        return (self.argtype, self.array_dim, self.struct)

    def gen_code(self) -> list[Decl]:
        return self.code

    def visit(self, node):
        # Store top 'Decl' node
        if isinstance(node, Decl):
            self.node = node

        return super().visit(node)

    # Entry node
    def visit_Decl(self, node: Decl) -> None:
        self.argname = node.name
        self.visit(node.type)

    # Common node
    def visit_TypeDecl(self, node: TypeDecl) -> None:
        self.visit(node.type)

        assert self.argname is not None
        assert self.argtype is not None

        argname = ID(self.argname)

        # Primitive or struct
        if not self.array_dim:
            if self.struct:
                generator = StructTypeGen(argname, self.argtype)
                self.code = generator.gen()
            else:
                generator = PrimitiveTypeGen(
                    argname,
                    self.argtype,
                    self.max_macro,
                    self.max_args,
                )
                self.code = generator.gen(self.default)

            return

        # Array or pointer
        argtype = "char" if self.argtype == "void" else self.argtype

        generator = ArrayTypeGen(
            argname,
            argtype,
            self.array_dim,
            self.struct,
            self.null,
        )
        self.code = generator.gen(self.default, self.concrete_arr)

    def visit_ArrayDecl(self, node: ArrayDecl) -> None:
        if node.dim is not None:
            self.array_dim.append(node.dim.value)
        else:
            self.array_dim.append("array")

        self.visit(node.type)

    def visit_PtrDecl(self, node: PtrDecl) -> None:
        # Function pointers are ignored.
        if isinstance(node.type, FuncDecl):
            return

        self.array_dim.append(self.size_macro)
        self.visit(node.type)

    def visit_Struct(self, node: Struct) -> None:
        self.argtype = f"struct {node.name}"
        self.struct = True

    def visit_IdentifierType(self, node: IdentifierType) -> None:
        self.argtype = " ".join(node.names)
