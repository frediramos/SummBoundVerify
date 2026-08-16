import claripy

from typing import Callable
from dataclasses import dataclass

from claripy.ast import Bool, true

from ...utils import (
    String,
    SymbString,
    constraint,
    eq_strings,
    neq_strings
)


type ConcrFileEntry = dict[str, int]


@dataclass(frozen=True, slots=True)
class SymbFileEntry:
    filename: SymbString
    fd: int


type FileEntry = ConcrFileEntry | SymbFileEntry


class SymbFileSystem():
    def __init__(self) -> None:
        self.fd = 0
        self.entries: list[FileEntry] = []

    def __copy__(self):
        fs = type(self)()
        fs.fd = self.fd
        fs.entries = [
            entry.copy() if isinstance(entry, dict) else entry
            for entry in self.entries
        ]
        return fs

    def _incr_fd(self) -> int:
        fd = self.fd
        self.fd += 1
        return fd

    def _is_concrete(self, entry):
        return isinstance(entry, dict)

    def _is_symbolic(self, entry):
        return isinstance(entry, SymbFileEntry)

    def is_emtpy(self):
        return len(self.entries) == 0

    def add(self, entry: FileEntry):
        self.entries.append(entry)

    @property
    def current(self):
        if self.is_emtpy():
            return None
        return self.entries[-1]

    def _create_concrete(self, filename: str) -> int:
        fd = self._incr_fd()
        if self._is_concrete(self.current):
            self.current[filename] = fd  # type: ignore
        else:
            entry = {}
            entry[filename] = fd

        self.add(entry)
        return fd

    def _create_symbolic(self, filename: SymbString):
        fd = self._incr_fd()
        entry = SymbFileEntry(filename, fd)
        self.add(entry)
        return fd

    def _cmp_filename(
        self,
        name: SymbString,
        op: Callable[[String, String], Bool]
    ):
        cases = []
        for entry in reversed(self.entries):
            if self._is_concrete(entry):
                assert isinstance(entry, dict)
                for k in entry:
                    c = op(name, k)
                    cases.append(c)
            else:
                assert isinstance(entry, SymbFileEntry)
                c = op(name, entry.filename)
                cases.append(c)

        return constraint(claripy.And, *cases)

    def eq_file(self, filename: SymbString):
        return self._cmp_filename(filename, eq_strings)

    def neq_file(self, filename: SymbString):
        return self._cmp_filename(filename, neq_strings)

    def create_file(self, filename: str | SymbString) -> tuple[int, Bool]:
        if isinstance(filename, str):
            fd = self._create_concrete(filename)
            return (fd, true())
        elif filename.is_symbolic():
            fd = self._create_concrete(str(filename))
            return (fd, true())
        else:
            fd = self._create_symbolic(filename)
            expr = self.neq_file(filename)
            return (fd, expr)
