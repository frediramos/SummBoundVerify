from typing import Any
from abc import ABC, abstractmethod

from pycparser.c_ast import (
    ID,
    Decl,
    Node,
    FuncDef,
    Compound,
    ExprList,
    FuncCall,
    FuncDecl,
    PtrDecl,
    TypeDecl,
    IdentifierType,
)

from .args import SymbolicArgGen
from .args.generators.types.array import ArrayTypeGen

from ..api import (
    mem_addr,
    file_create,
    file_open,
    file_write,
    file_set_offset,
    FILE_from_fd,
)


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

    def _gen_file_setup(self) -> tuple[list[Node], set[str]]:
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

        for entry in fd_args:
            name = entry['name']
            ftype = entry['file_type']
            fname_spec = entry['fname']
            data_spec = entry['data']

            fname_size = fname_spec.get('size', 5)
            fname_var = f"__fname_{name}"

            skip.add(name)

            # Symbolic file name array
            fname_gen = ArrayTypeGen(ID(fname_var), "char", [str(fname_size)])
            setup.extend(fname_gen.gen())

            # __file_create(fname)
            setup.append(file_create(fname_var))

            if ftype == 'descriptor':
                # int <name> = __file_open(fname, "w")
                setup.append(file_open(name, fname_var))
                fd_var = name
            else:
                # FILE* pointer: use a temp fd, then convert
                fd_var = f"__fd_{name}"
                setup.append(file_open(fd_var, fname_var))

            # Optional initial data
            if data_spec:
                data_size = data_spec.get('size', 5)
                data_symbolic = data_spec.get('symbolic', False)
                data_var = f"__data_{name}"

                if data_symbolic:
                    # Allocate size+1 so the null terminator doesn't eat a data byte
                    alloc_size = data_size + 1
                    data_gen = ArrayTypeGen(ID(data_var), "char", [str(alloc_size)])
                    setup.extend(data_gen.gen())
                else:
                    # Concrete zero-filled array (declaration only, no symbolic init)
                    data_gen = ArrayTypeGen(ID(data_var), "char", [str(data_size)])
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
