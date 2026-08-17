import claripy

from copy import copy
from typing import Callable
from dataclasses import dataclass

from angr import SimState

from claripy import BVV
from claripy.ast import Bool, BV

from ...utils import (
    String,
    SymbString,
    constraint,
    eq_strings,
    neq_strings
)


@dataclass(frozen=True, slots=True)
class File:
    fd: int


type ConcrFileEntry = dict[str, File]


@dataclass(frozen=True, slots=True)
class SymbFileEntry:
    filename: SymbString
    fd: File


type FileEntry = ConcrFileEntry | SymbFileEntry


class SymbFileSystem():
    """Symbolic File System Modelling"""

    def __init__(self, state: SimState) -> None:
        """
        Initialize an empty file system.

        File descriptor allocation starts at `3`.

        File descriptors `0`, `1`, and `2` are reserved
        for `stdin`, `stdout`, and `stderr`, repectively.
        """
        self.state = state

        self.fd = 3
        self.entries: list[FileEntry] = []

    def clone(self, state: SimState) -> "SymbFileSystem":
        """Create a copy associated with the given state."""
        fs = type(self)(state)
        fs.fd = self.fd
        fs.entries = [
            dict(entry) if isinstance(entry, dict)
            else SymbFileEntry(copy(entry.filename), entry.fd)
            for entry in self.entries
        ]
        return fs

    def _bvv_int(self, value: int):
        int_bits = self.state.arch.sizeof["int"]
        return BVV(value, int_bits)

    def _incr_fd(self) -> int:
        fd = self.fd
        self.fd += 1
        return fd

    def _closed(self) -> File:
        return File(fd=-1)

    def is_concrete(self, entry):
        """Return whether an entry represents concrete files."""
        return isinstance(entry, dict)

    def is_symbolic(self, entry):
        """Return whether an entry represents a symbolic file."""
        return isinstance(entry, SymbFileEntry)

    def is_sat(self, cnstr):
        return self.state.solver.satisfiable(extra_constraints=(cnstr,))

    def is_emtpy(self):
        """Return whether the file system contains no entries."""
        return len(self.entries) == 0

    def add(self, entry: FileEntry):
        """Add a file entry to the file system."""
        self.entries.append(entry)

    @property
    def current(self):
        """Return the most recently added file entry, or None if empty."""
        if self.is_emtpy():
            return None
        return self.entries[-1]

    def compare_filename(
        self,
        name: str | SymbString,
        op: Callable[[String, String], Bool]
    ):
        """Apply a filename comparison to all files in the file system."""
        cases = []
        for entry in reversed(self.entries):
            if self.is_concrete(entry):
                assert isinstance(entry, dict)
                for k in entry:
                    c = op(name, k)
                    cases.append(c)
            else:
                assert isinstance(entry, SymbFileEntry)
                c = op(name, entry.filename)
                cases.append(c)

        return constraint(claripy.And, *cases)

    def search_filename(self, name: str | SymbString) -> BV:
        """
        Search for `filename` in the file system.
        Returns an if-then-else constraint value for the fd.
        """
        cases = []
        for entry in reversed(self.entries):
            if self.is_concrete(entry):
                assert isinstance(entry, dict)
                for k, v in entry.items():
                    c = eq_strings(name, k)
                    fd = self._bvv_int(v.fd)
                    cases.append((c, fd))
            else:
                assert isinstance(entry, SymbFileEntry)
                c = eq_strings(name, entry.filename)
                cases.append((c, entry.fd))

        return claripy.ite_cases(cases, self._bvv_int(-1))

    def eq_file(self, filename: str | SymbString):
        return self.compare_filename(filename, eq_strings)

    def neq_file(self, filename: str | SymbString):
        return self.compare_filename(filename, neq_strings)

    def _set_concrete(self, filename: str, file: File):
        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)
            self.current[filename] = file
        else:
            entry = {}
            entry[filename] = file

        self.add(entry)

    def _set_symbolic(self, filename: SymbString, file: File):
        entry = SymbFileEntry(filename, file)
        self.add(entry)

    def _create_concrete(self, filename: str) -> int:
        fd = self._incr_fd()
        file = File(fd)
        self._set_concrete(filename, file)
        return fd

    def _create_symbolic(self, filename: SymbString):
        fd = self._incr_fd()
        file = File(fd)
        self._set_symbolic(filename, file)
        return fd

    def create_concrete(self, filename: str) -> int:
        """Create a concrete file and return its file descriptor."""
        if self.is_emtpy():
            return self._create_concrete(filename)

        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)
            if filename in self.current:
                return -1

        # File not exists constraint
        constraint = self.neq_file(filename)

        if self.is_sat(constraint):
            self.state.add_constraints(constraint)
            return self._create_concrete(filename)

        return -1

    def create_symbolic(self, filename: SymbString) -> int:
        """Create a symbolic file and return its file descriptor."""
        if self.is_emtpy():
            return self._create_symbolic(filename)

        # File not exists constraint
        constraint = self.neq_file(filename)

        if self.is_sat(constraint):
            self.state.add_constraints(constraint)
            return self._create_symbolic(filename)

        return -1

    def create_file(self, filename: str | SymbString) -> int:
        """
        Create a file and return its descriptor.
        Returns `-1` on error.

        Adds the required constraints to the path condition
        """
        if isinstance(filename, str):
            return self.create_concrete(filename)
        else:
            assert isinstance(filename, SymbString)
            return self.create_symbolic(filename)

    def close_concrete(self, filename: str) -> int:
        if self.is_emtpy():
            return -1

        # File exists constraint
        constraint = self.eq_file(filename)

        if self.is_sat(constraint):
            self.state.add_constraints(constraint)
            self._set_concrete(filename, self._closed())
            return 1

        return -1

    def close_symbolic(self, filename:  SymbString) -> int:
        if self.is_emtpy():
            return -1

        # File exists constraint
        constraint = self.eq_file(filename)

        if self.is_sat(constraint):
            self.state.add_constraints(constraint)
            self._set_symbolic(filename, self._closed())
            return 1

        return -1

    def close_file(self, filename: str | SymbString) -> int:
        """
        Closes a file.
        Returns `1` on success.
        Returns `-1` on error.

        Adds the required constraints to the path condition
        """
        if isinstance(filename, str):
            return self.close_concrete(filename)
        else:
            assert isinstance(filename, SymbString)
            return self.close_symbolic(filename)

    def open_concrete(self, filename: str) -> int | BV:
        """Open a concrete file name and return its file descriptor."""
        if self.is_emtpy():
            return -1

        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)
            if filename in self.current: 
                file = self.current[filename]
                return file.fd

        # File not exists constraint
        fd = self.search_filename(filename)

        return fd

    def open_symbolic(self, filename: SymbString) -> int | BV:
        """Open a symbolic file and return its file descriptor."""
        if self.is_emtpy():
            return -1

        # File not exists constraint
        fd = self.search_filename(filename)

        return fd

    def open_file(self, filename: str | SymbString) -> int | BV:
        """
        Opens a file and return its descriptor. Return can be symbolic.
        Returns `-1` on error.
        """
        if isinstance(filename, str):
            return self.open_concrete(filename)
        else:
            assert isinstance(filename, SymbString)
            return self.open_symbolic(filename)
