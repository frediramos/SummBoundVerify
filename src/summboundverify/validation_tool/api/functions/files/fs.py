import claripy

from copy import copy
from dataclasses import dataclass

from angr import SimState

from claripy import BVV, true
from claripy.ast import Bool, BV

from ...utils import (
    String,
    SymbString,
    constraint,
    eq_strings,
)


@dataclass(frozen=True, slots=True)
class File:
    fd: int


type ConcrFileEntry = dict[str, File | None]


@dataclass(frozen=True, slots=True)
class SymbFileEntry:
    filename: SymbString
    file: File | None


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
            else SymbFileEntry(copy(entry.filename), copy(entry.file))
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

    def is_certain(self, cnstr):
        neg_cnstr = claripy.Not(cnstr)
        return not self.state.solver.satisfiable(extra_constraints=(neg_cnstr,))

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

    def file_exists(self, filename: str | SymbString) -> Bool:
        """Return a constraint indicating whether `filename` exists."""
        cases = []

        for entry in reversed(self.entries):
            if self.is_concrete(entry):
                assert isinstance(entry, dict)
                files = entry.items()
            else:
                assert isinstance(entry, SymbFileEntry)
                files = [(entry.filename, entry.file)]

            for name, file in files:
                if file is None:
                    continue

                condition = eq_strings(filename, name)

                if self.is_certain(condition):
                    return true()

                cases.append(condition)

        return constraint(claripy.Or, *cases)

    def file_not_exists(self, filename: str | SymbString) -> Bool:
        exists = self.file_exists(filename)
        not_exits = claripy.Not(exists)
        return not_exits

    def search_filename(self, name: str | SymbString) -> BV:
        """Return the file descriptor associated with `name`, or -1 if not found."""
        cases = []

        for entry in reversed(self.entries):
            if self.is_concrete(entry):
                assert isinstance(entry, dict)
                files = entry.items()
            else:
                assert isinstance(entry, SymbFileEntry)
                files = [(entry.filename, entry.file)]

            for filename, file in files:
                condition = eq_strings(name, filename)
                fd = self._bvv_int(-1 if file is None else file.fd)

                if self.is_certain(condition):
                    return fd

                cases.append((condition, fd))

        return claripy.ite_cases(cases, self._bvv_int(-1))

    def _set_concrete(self, filename: str, file: File | None):
        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)
            self.current[filename] = file
        else:
            entry = {}
            entry[filename] = file

        self.add(entry)

    def _set_symbolic(self, filename: SymbString, file: File | None):
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
            if (
                filename in self.current and
                # None -> file was deleted before
                self.current[filename] is not None
            ):
                return -1

        # File not exists constraint
        constraint = self.file_not_exists(filename)

        if self.is_sat(constraint):
            self.state.add_constraints(constraint)
            return self._create_concrete(filename)

        return -1

    def create_symbolic(self, filename: SymbString) -> int:
        """Create a symbolic file and return its file descriptor."""
        if self.is_emtpy():
            return self._create_symbolic(filename)

        constraint = self.file_not_exists(filename)

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

        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)
            if (
                filename in self.current and
                # None -> file was deleted before
                self.current[filename] is not None
            ):
                self.current[filename] = File(fd=-1)

        constraint = self.file_exists(filename)

        if self.is_sat(constraint):
            self.state.add_constraints(constraint)
            self._set_concrete(filename, self._closed())
            return 1

        return -1

    def close_symbolic(self, filename:  SymbString) -> int:
        if self.is_emtpy():
            return -1

        constraint = self.file_exists(filename)

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
                if file is not None:
                    return file.fd

        fd = self.search_filename(filename)

        return fd

    def open_symbolic(self, filename: SymbString) -> int | BV:
        """Open a symbolic file and return its file descriptor."""
        if self.is_emtpy():
            return -1

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
            ret = self.open_symbolic(filename)
            return ret

    def delete_concrete(self, filename: str) -> int:
        if self.is_emtpy():
            return -1

        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)
            if filename in self.current:
                del self.current[filename]
                return 1

        constraint = self.file_exists(filename)

        if self.is_sat(constraint):
            self.state.add_constraints(constraint)
            self._set_concrete(filename, None)
            return 1

        return -1

    def delete_symbolic(self, filename: SymbString) -> int:
        if self.is_emtpy():
            return -1

        constraint = self.file_exists(filename)

        if self.is_sat(constraint):
            self.state.add_constraints(constraint)
            self._set_symbolic(filename, None)
            return 1

        return -1

    def delete_file(self, filename: str | SymbString) -> int | BV:
        """
        Deletes a file.
        Returns `1` on success.
        Returns `-1` on error.

        Adds the required constraints to the path condition
        """
        if isinstance(filename, str):
            return self.delete_concrete(filename)
        else:
            assert isinstance(filename, SymbString)
            return self.delete_symbolic(filename)
