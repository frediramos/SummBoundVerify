from typing import Any
from abc import ABC, abstractmethod

from pycparser.c_ast import (
    ID,
    For,
    Decl,
    Node,
    FuncDef,
    UnaryOp,
    BinaryOp,
    Compound,
    ExprList,
    FuncCall,
    FuncDecl,
    PtrDecl,
    TypeDecl,
    Constant,
    ArrayRef,
    DeclList,
    IdentifierType,
)

from .args import SymbolicArgGen
from .args.generators.types.array import ArrayTypeGen

from ..api import (
    mem_addr,
    file_addr,
    file_create,
    file_open,
    file_write,
    file_set_offset,
    FILE_from_fd,
)

from summboundverify.api import api_map
from summboundverify.validation_gen.utils import Macros, get_defined_macro


class TestGen(ABC):
    """Common functionality for generating validation tests."""

    def __init__(
        self,
        args: list[Node] | None,
        ret: Decl,
        max_args: list[Any] | None,
        argspec: dict | None = None,
    ) -> None:
        self.args = args
        self.ret = ret
        self.max_args = max_args or []
        self.argspec = argspec or {}

    @staticmethod
    def _returns_void(node: Node) -> bool:
        return isinstance(node, TypeDecl) and node.type.names == ["void"]

    @staticmethod
    def _returns_pointer(node: Node) -> bool:
        return isinstance(node, PtrDecl)

    def _call_function(
        self,
        name: str,
        call_args: list[str],
        ret_name: str,
    ) -> Node:

        call = FuncCall(
            ID(name),
            ExprList([ID(arg) for arg in call_args]),
        )

        if self._returns_void(self.ret):
            return call

        lvalue = TypeDecl(ret_name, [], None, self.ret)

        return Decl(
            ret_name,
            [], [], [], [],
            lvalue,
            call,
            None,
        )

    @staticmethod
    def _tag_memory(ptr_names: list[str], size_macro: str | list[str] | None) -> list[Node]:

        if isinstance(size_macro, list):
            return [
                mem_addr(ptr, size)
                for ptr, size in zip(ptr_names, size_macro)
            ]

        return [mem_addr(ptr, size_macro) for ptr in ptr_names]

    def _memory_args(self, sym_args) -> list[str]:
        """Return pointer args that should be tagged with __mem_addr."""
        mem_args = []
        for name in sym_args.pointer_args:
            spec = self.argspec.get(name, {})
            semantic = spec.get('semantic', 'scalar')
            if semantic == 'memory':
                mem = spec.get('memory', {})
                if mem.get('type', 'write') == 'write':
                    mem_args.append(name)
        return mem_args

    def _file_descriptor_args(self) -> list[dict]:
        """Collect argspec entries for descriptor and pointer file args."""
        results = []
        for name, spec in self.argspec.items():
            if spec.get('semantic') != 'file':
                continue
            fblock = spec.get('file', {})
            ftype = fblock.get('type', 'descriptor')
            if ftype in ('descriptor', 'pointer'):
                results.append({
                    'name': name,
                    'file_type': ftype,
                    'fname': fblock.get('fname', {}),
                    'data': fblock.get('data', {}),
                })
        return results

    def _file_name_args(self) -> list[str]:
        """Collect argspec entries where the argument is a file path (type: name)."""
        results = []
        for name, spec in self.argspec.items():
            if spec.get('semantic') != 'file':
                continue
            fblock = spec.get('file', {})
            if fblock.get('type') == 'name':
                results.append(name)
        return results

    def _tag_files(self) -> list[Node]:
        """Generate __file_addr calls for name-type file args."""
        return [file_addr(name) for name in self._file_name_args()]

    @staticmethod
    def _filename_constraints(
        fname_var: str,
        fname_size: int,
        use_api: bool = False,
    ) -> list[Node]:
        """Generate __assume constraints excluding invalid filenames.

        Excludes: empty string, '/', '.', '..' from the symbolic filename.

        When use_api is True, comparisons go through _NEQ_/_OR_ so the SE
        engine registers them in the CNSTR_MAP.  When False, raw C operators
        are emitted (suitable for the concrete/AFL harness).
        """

        def neq(a, b):
            if use_api:
                return FuncCall(ID('_NEQ_'), ExprList([a, b]))
            return BinaryOp('!=', a, b)

        def or_expr(a, b):
            if use_api:
                return FuncCall(ID('_OR_'), ExprList([a, b]))
            return BinaryOp('|', a, b)

        assume = api_map().assume
        nodes: list[Node] = []

        # Non-empty: first byte must not be null
        nodes.append(FuncCall(ID(assume), ExprList([
            neq(
                ArrayRef(ID(fname_var), Constant('int', '0')),
                Constant('int', '0'),
            ),
        ])))

        # Not "."
        if fname_size >= 2:
            not_dot = or_expr(
                neq(
                    ArrayRef(ID(fname_var), Constant('int', '0')),
                    Constant('char', "'.'")
                ),
                neq(
                    ArrayRef(ID(fname_var), Constant('int', '1')),
                    Constant('int', '0')
                )
            )
            nodes.append(FuncCall(ID(assume), ExprList([not_dot])))

        # Not ".."
        if fname_size >= 3:
            not_dotdot = or_expr(
                or_expr(
                    neq(
                        ArrayRef(ID(fname_var), Constant('int', '0')),
                        Constant('char', "'.'")
                    ),

                    neq(
                        ArrayRef(ID(fname_var), Constant('int', '1')),
                        Constant('char', "'.'")
                    ),
                ),
                neq(
                    ArrayRef(ID(fname_var), Constant('int', '2')),
                    Constant('int', '0')
                )
            )
            nodes.append(FuncCall(ID(assume), ExprList([not_dotdot])))

        # No '/' in any byte
        loop_var = f"__i_{fname_var}"
        loop_init = DeclList(
            [
                Decl(
                    loop_var, [], [], [], [],
                    TypeDecl(
                        loop_var, [], None,
                        IdentifierType(names=["int"])
                    ),
                    Constant('int', '0'), None
                )
            ]
        )

        loop_cond = BinaryOp(
            '<', ID(loop_var),
            Constant('int', str(fname_size))
        )

        loop_next = UnaryOp('p++', ID(loop_var))
        loop_body = Compound(
            block_items=[
                FuncCall(
                    ID(assume),
                    ExprList([neq(
                        ArrayRef(ID(fname_var), ID(loop_var)),
                        Constant('char', "'/'")
                    )])
                )
            ]
        )
        nodes.append(For(loop_init, loop_cond, loop_next, loop_body))

        return nodes

    def _gen_name_file_constraints(self, use_api: bool = False) -> list[Node]:
        """Generate filename constraints for name-type file args."""
        nodes: list[Node] = []
        for name, spec in self.argspec.items():
            if spec.get('semantic') != 'file':
                continue

            fblock = spec.get('file', {})
            if fblock.get('type') != 'name':
                continue

            fname_size = fblock.get('fname', {}).get('size', 5)
            nodes.extend(
                self._filename_constraints(
                    name,
                    fname_size,
                    use_api=use_api
                )
            )
        return nodes

    def _gen_file_setup(self, use_api: bool = False) -> tuple[list[Node], set[str]]:
        """Generate file setup code for descriptor/pointer file args.

        Returns:
            setup_code: AST nodes to prepend to the test body (before save_current_state).
            skip_names: Arg names to skip in SymbolicArgGen.
        """
        fd_args = self._file_descriptor_args()
        if not fd_args:
            return [], set()

        setup: list[Node] = []
        skip = set()

        for i, entry in enumerate(fd_args, 1):
            name = entry['name']
            ftype = entry['file_type']
            data_spec = entry['data']

            fname_size_macro = f"{Macros.FNAME_SIZE}_{i}"
            fname_size = get_defined_macro(fname_size_macro)
            fname_var = f"__fname_{name}"

            skip.add(name)

            # Symbolic file name array
            fname_gen = ArrayTypeGen(
                ID(fname_var),
                "char",
                [fname_size_macro]
            )
            setup.extend(fname_gen.gen())

            setup.extend(
                self._filename_constraints(
                    fname_var,
                    fname_size,
                    use_api=use_api
                )
            )

            # __file_create(fname)
            setup.append(file_create(fname_var))

            if ftype == 'descriptor':
                flags = "w+" if data_spec else "w"
                setup.append(file_open(name, fname_var, flags))
                fd_var = name
            else:
                # FILE* pointer: use a temp fd, then convert
                fd_var = f"__fd_{name}"
                flags = "w+" if data_spec else "w"
                setup.append(file_open(fd_var, fname_var, flags))

            # Optional initial data
            if data_spec:
                data_size = data_spec.get('size', 5)
                data_symbolic = data_spec.get('symbolic', False)
                data_var = f"__data_{name}"

                if data_symbolic:
                    # Allocate size+1 so the null terminator doesn't eat a data byte
                    alloc_size = data_size + 1
                    data_gen = ArrayTypeGen(
                        ID(data_var), "char", [str(alloc_size)])
                    setup.extend(data_gen.gen())
                else:
                    # Concrete zero-filled array (declaration only, no symbolic init)
                    data_gen = ArrayTypeGen(
                        ID(data_var),
                        "char",
                        [str(data_size)]
                    )

                    setup.extend(data_gen.gen(const=0))

                setup.append(file_write(fd_var, data_var, data_size))
                setup.append(file_set_offset(fd_var, 0))

            if ftype == 'pointer':
                # FILE* <name> = __FILE_from_fd(__fd_<name>)
                setup.append(FILE_from_fd(name, fd_var))

        return setup, skip

    def _create_args(
        self,
        size_macro: str | list[str] | None,
        null_bytes: list[Any] | None,
        max_macro: Any,
        default: dict[int, Any] | None,
        concrete: dict[int, Any] | None,
        skip: set[str] | None = None,

    ) -> tuple[list[Node], list[str], SymbolicArgGen]:

        sym_args = SymbolicArgGen(
            self.args,
            size_macro,
            null_bytes,
            max_macro,
            self.max_args,
            skip=skip,
        )

        args_code = sym_args.create_symbolic_args(default, concrete)

        return args_code, sym_args.call_args, sym_args

    @staticmethod
    def _function(name: str, body: list[Node]) -> FuncDef:
        decl = Decl(
            name,
            [], [], [], [],
            FuncDecl(
                None,
                TypeDecl(
                    name, [], None,
                    IdentifierType(names=["void"]),
                ),
            ),
            None, None
        )

        return FuncDef(decl, None, Compound(body))

    @abstractmethod
    def create_test(
        self,
        name: str,
        size_macro: str | list[str] | None,
        null_bytes: list[Any] | None,
        max_macro: Any,
        default: dict[int, Any] | None,
        concrete: dict[int, Any] | None,
        test_id: int,
    ) -> FuncDef:
        pass
