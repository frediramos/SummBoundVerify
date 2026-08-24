import angr
import claripy

from copy import copy
from typing import Callable, Iterator
from dataclasses import dataclass

from angr import SimState
from cle.backends.externs.simdata.io_file import io_file_data_for_arch

from claripy import BVV, true
from claripy.ast import Bool, BV

from ...utils import (
    SymbString,
    constraint,
    eq_strings,
    neq_strings
)


@dataclass(slots=True)
class File:

    """State of an open file."""

    fd: int
    fp: int
    size: int = 0
    offset: int = 0


@dataclass(slots=True)
class FdEntry:
    cond: Bool
    file: File


type NameConcreteEntry = dict[str, list[FdEntry] | None]


@dataclass(frozen=True, slots=True)
class NameSymbolicEntry:

    """
    A file whose name is represented by a symbolic string.

    A `None` file represents a deleted file.
    A `File` with `fd = -1` represents a closed file.
    """

    filename: SymbString
    entries: list[FdEntry] | None


type NameFileEntry = NameConcreteEntry | NameSymbolicEntry


class SymbFileSystem:
    """Model of a file system with concrete and symbolic file names."""

    def __init__(self, state: SimState) -> None:
        """Initialize an empty file system.

        File descriptor allocation starts at 3. Descriptors 0, 1, and 2
        are reserved for stdin, stdout, and stderr, respectively.
        """
        self.state = state
        self.fd = 3
        self.entries: list[NameFileEntry] = []

    def clone(self, state: SimState) -> "SymbFileSystem":
        """
        Create an independent copy of the file system for `state`.
        """
        fs = type(self)(state)
        fs.fd = self.fd
        fs.entries = [self._clone_entry(entry) for entry in self.entries]
        return fs

    def _clone_entry(self, entry: NameFileEntry) -> NameFileEntry:
        if isinstance(entry, dict):
            return self._clone_concrete_entry(entry)

        return self._clone_symbolic_entry(entry)

    def _clone_concrete_entry(self, entry: NameConcreteEntry) -> NameConcreteEntry:
        return {
            name: None if fd_entries is None
            else self._clone_fd_entries(fd_entries)
            for name, fd_entries in entry.items()
        }

    def _clone_symbolic_entry(self, entry: NameSymbolicEntry) -> NameSymbolicEntry:
        entries = (
            None
            if entry.entries is None
            else self._clone_fd_entries(entry.entries)
        )
        return NameSymbolicEntry(copy(entry.filename), entries)

    def _clone_fd_entries(self, entries: list[FdEntry]) -> list[FdEntry]:
        return [self._clone_fd_entry(entry) for entry in entries]

    def _clone_fd_entry(self, entry: FdEntry) -> FdEntry:
        return FdEntry(entry.cond, copy(entry.file))

    def bvv_int(self, value: int):
        """Create a bit-vector containing a C `int` value."""
        int_bits = self.state.arch.sizeof["int"]
        return BVV(value, int_bits)

    def incr_fd(self) -> int:
        fd = self.fd
        self.fd += 1
        return fd

    def is_concrete(self, entry):
        """Return whether `entry` contains concrete file names."""
        return isinstance(entry, dict)

    def is_symbolic(self, entry):
        """Return whether `entry` contains a symbolic file name."""
        return isinstance(entry, NameSymbolicEntry)

    def is_sat(self, cnstr):
        """Return whether `cnstr` is satisfiable under the current path condition."""
        return self.state.solver.satisfiable(extra_constraints=(cnstr,))

    def call_simproc(self, procedure, *args, **kwargs):
        e_args = [
            claripy.BVV(a, self.state.arch.bits)
            if isinstance(a, int) else a for a in args
        ]
        p = procedure(project=self.state.project, **kwargs)
        return p.execute(self.state, None, arguments=e_args)

    def is_certain(self, cnstr):
        """Return whether `cnstr` is necessarily true under the current path condition."""
        neg_cnstr = claripy.Not(cnstr)
        return not self.state.solver.satisfiable(
            extra_constraints=(neg_cnstr,)
        )

    def is_emtpy(self):
        """Return whether the file system contains no entries."""
        return len(self.entries) == 0

    def add(self, entry: NameFileEntry):
        """Append an entry to the file system."""
        self.entries.append(entry)

    @property
    def current(self):
        """Return the most recently added entry, or `None` if empty."""
        if self.is_emtpy():
            return None
        return self.entries[-1]

    def _create_fp(self, fd: int):
        malloc = angr.SIM_PROCEDURES["libc"]["malloc"]
        io_file_data = io_file_data_for_arch(self.state.arch)
        fp = self.call_simproc(malloc, io_file_data["size"]).ret_expr
        size = self.state.arch.sizeof["int"]

        # Write the fd
        self.state.memory.store(
            fp + io_file_data["fd"],
            fd,
            size=size,
            endness=self.state.arch.memory_endness
        )
        return fp

    def _create_file(self, fd: int | None = None) -> File:
        if fd is None:
            fd = self.incr_fd()
        fp = self._create_fp(fd)
        file = File(fd=fd, fp=fp)
        return file

    def _create_fd_entry(self, file: File) -> FdEntry:
        fd_entry = FdEntry(true(), file)
        return fd_entry

    def _closed_file(self) -> File:
        """Return a file object representing a closed file."""
        file = self._create_file(-1)
        return file

    def _closed_fd_entry(self) -> FdEntry:
        file = self._closed_file()
        fd_entry = self._create_fd_entry(file)
        return fd_entry

    def _set_concrete_fname(self, filename: str, fd_entry: FdEntry | None):
        """Add a concrete file entry, reusing the current concrete entry when possible."""
        entry = [fd_entry] if fd_entry is not None else None
        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)
            if filename in self.current:
                self.current[filename] = entry
        else:
            self.add({filename: entry})

    def _set_symbolic_fname(self, filename: SymbString, fd_entry: FdEntry | None):
        """Add a symbolic file entry."""
        entry = [fd_entry] if fd_entry is not None else None
        entry = NameSymbolicEntry(filename, entry)
        self.add(entry)

    def _create_concrete(self, filename: str) -> int:
        file = self._create_file()
        fd = file.fd
        fd_entry = self._create_fd_entry(file)
        self._set_concrete_fname(filename, fd_entry)
        return fd

    def _create_symbolic(self, filename: SymbString):
        file = self._create_file()
        fd = file.fd
        fd_entry = self._create_fd_entry(file)
        self._set_symbolic_fname(filename, fd_entry)
        return fd

    def _get_first_file(self, fd_entries: list[FdEntry]) -> File:
        """Get first `File` from a list of entries"""
        entry = fd_entries[0]
        assert entry.cond == true()
        return entry.file

    def file_exists_constraint(self, filename: str | SymbString) -> Bool:
        """Return a constraint indicating whether `filename` exists."""
        cases = []

        for entry in reversed(self.entries):
            if isinstance(entry, dict):
                fnames = [
                    name for name, entries in entry.items()
                    if entries is not None
                ]
            else:
                assert isinstance(entry, NameSymbolicEntry)
                fnames = (
                    [entry.filename]
                    if entry.entries is not None
                    else []
                )

            for name in fnames:

                condition = eq_strings(filename, name)

                if self.is_certain(condition):
                    return true()

                if self.is_sat(condition):
                    cases.append(condition)

        return constraint(claripy.Or, *cases)

    def file_not_exists_constraint(self, filename: str | SymbString) -> Bool:
        """Return a constraint indicating that `filename` does not exist."""
        exists = self.file_exists_constraint(filename)
        return claripy.Not(exists)

    def _iter_fd_entries(
        self,
        entry: NameFileEntry,
    ) -> Iterator[tuple[str | SymbString, Bool, File | None]]:

        if isinstance(entry, dict):
            for filename, entries in entry.items():
                if entries is None:
                    yield filename, true(), None
                else:
                    for fd_entry in entries:
                        yield filename, fd_entry.cond, fd_entry.file
        else:
            assert isinstance(entry, NameSymbolicEntry)
            if entry.entries is None:
                yield entry.filename, true(), None
            else:
                for fd_entry in entry.entries:
                    yield entry.filename, fd_entry.cond, fd_entry.file

    def search_by_filename(
        self,
        name: str | SymbString,
    ) -> list[tuple[Bool, File | None]]:
        """
        Return possible files matching `name` and their conditions.
        """
        cases = []

        for entry in reversed(self.entries):
            for filename, cond, file in self._iter_fd_entries(entry):

                condition = claripy.And(
                    eq_strings(name, filename),
                    cond,
                )

                if self.is_certain(condition):
                    return [(true(), file)]

                if self.is_sat(condition):
                    cases.append((condition, file))

        return cases

    def get_fd_by_name(self, name: str | SymbString) -> BV:
        """Return the file descriptor for `name`, or -1 if not found."""

        def fd(file: File | None) -> BV:
            return self.bvv_int(-1 if file is None else file.fd)

        minus_one = self.bvv_int(-1)
        cases = self.search_by_filename(name)
        mapped = ((condition, fd(file)) for condition, file in cases)

        return claripy.ite_cases(mapped, minus_one)

    def search_exists(self, name: str | SymbString) -> BV:
        """Return `1` if file `name` exists, or `0` otherwise."""

        def exists(file: File | None) -> BV:
            return self.bvv_int(0 if (file is None or file.fd == -1) else 1)

        zero = self.bvv_int(0)
        cases = self.search_by_filename(name)
        mapped = ((condition, exists(file)) for condition, file in cases)

        return claripy.ite_cases(mapped, zero)

    def search_by_field(
        self,
        value: int | BV,
        getter: Callable[[File], int | BV],
    ) -> list[tuple[Bool, File | None]]:
        """
        Return possible files matching `value` for the given `field`.
        """
        cases = []
        deleted = []

        for entry in reversed(self.entries):
            for filename, cond, file in self._iter_fd_entries(entry):

                if file is None or file.fd == -1:
                    deleted.append(filename)
                    continue

                neq = constraint(
                    claripy.And,
                    *[neq_strings(filename, d) for d in deleted]
                )

                v = getter(file)
                condition = claripy.And(value == v, neq, cond)

                if self.is_certain(condition):
                    return [(true(), file)]

                if self.is_sat(condition):
                    cases.append((condition, file))

        return cases

    def get_fp_from_fd(self, fd: int | BV):
        def getter(file: File): return file.fd

        def fp(file: File | None) -> BV:
            return self.bvv_int(
                0 if (file is None or file.fd == -1)
                else file.fp
            )

        null = self.bvv_int(0)
        cases = self.search_by_field(fd, getter)
        mapped = ((condition, fp(file)) for condition, file in cases)

        return claripy.ite_cases(mapped, null)

    def get_fd_from_fp(self, fp: int | BV):
        def getter(file: File): return file.fp

        def fd(file: File | None) -> BV:
            return self.bvv_int(
                -1 if (file is None or file.fp == -1)
                else file.fd
            )

        err = self.bvv_int(-1)
        cases = self.search_by_field(fp, getter)
        mapped = ((condition, fd(file)) for condition, file in cases)

        return claripy.ite_cases(mapped, err)

    def create_concrete(self, filename: str) -> int:
        """Create a concrete file.

        Returns its file descriptor, or -1 if the file already exists or
        the required path condition is unsatisfiable.
        """
        if self.is_emtpy():
            return self._create_concrete(filename)

        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)
            if (
                filename in self.current
                and self.current[filename] is not None
            ):
                return -1

        # Creating the file requires the filename not to already exist.
        cnstr = self.file_not_exists_constraint(filename)

        if self.is_sat(cnstr):
            self.state.add_constraints(cnstr)
            return self._create_concrete(filename)

        return -1

    def create_symbolic(self, filename: SymbString) -> int:
        """Create a symbolic file.

        Returns its file descriptor, or -1 if the file already exists or
        the required path condition is unsatisfiable.
        """
        if self.is_emtpy():
            return self._create_symbolic(filename)

        cnstr = self.file_not_exists_constraint(filename)

        if self.is_sat(cnstr):
            self.state.add_constraints(cnstr)
            return self._create_symbolic(filename)

        return -1

    def create_file(self, filename: str | SymbString) -> int:
        """
        Create a file and return its file descriptor.

        Returns `-1` on failure. When necessary, the constraints required
        to establish that the file does not already exist are added to
        the current path condition.
        """
        if isinstance(filename, str):
            return self.create_concrete(filename)

        assert isinstance(filename, SymbString)
        return self.create_symbolic(filename)

    def close_concrete(self, filename: str) -> int:
        """Close a concrete file and return 1 on success or -1 on failure."""
        if self.is_emtpy():
            return -1

        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)

            if filename in self.current:
                if self.current[filename] is not None:
                    self.current[filename] = [self._closed_fd_entry()]
                    return 1
                else:
                    return -1

        cnstr = self.file_exists_constraint(filename)

        if self.is_sat(cnstr):
            self.state.add_constraints(cnstr)
            self._set_concrete_fname(filename, self._closed_fd_entry())
            return 1

        return -1

    def close_symbolic(self, filename: SymbString) -> int:
        """Close a symbolic file and return 1 on success or -1 on failure."""
        if self.is_emtpy():
            return -1

        cnstr = self.file_exists_constraint(filename)

        if self.is_sat(cnstr):
            file = self._closed_file()
            fd_entry = self._create_fd_entry(file)
            self.state.add_constraints(cnstr)
            self._set_symbolic_fname(filename, fd_entry)
            return 1

        return -1

    def close_file(self, filename: str | SymbString) -> int:
        """
        Close a file.

        Returns `1` on success and `-1` on failure. When necessary, the
        required existence constraint is added to the path condition.
        """
        if isinstance(filename, str):
            return self.close_concrete(filename)

        assert isinstance(filename, SymbString)
        return self.close_symbolic(filename)

    def open_concrete(self, filename: str) -> int | BV:
        """Open a concrete file name and return its file descriptor."""
        if self.is_emtpy():
            return -1

        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)
            if filename in self.current:
                entries = self.current[filename]
                if entries is not None:
                    file = self._get_first_file(entries)
                    return file.fd

        return self.get_fd_by_name(filename)

    def open_symbolic(self, filename: SymbString) -> int | BV:
        """Open a symbolic file name and return its file descriptor."""
        if self.is_emtpy():
            return -1

        return self.get_fd_by_name(filename)

    def open_file(self, filename: str | SymbString) -> int | BV:
        """
        Open a file and return its descriptor, which may be symbolic.

        Returns `-1` if the file system is empty or the file cannot be found.
        """
        if isinstance(filename, str):
            return self.open_concrete(filename)

        assert isinstance(filename, SymbString)
        return self.open_symbolic(filename)

    def delete_concrete(self, filename: str) -> int:
        """Delete a concrete file and return 1 on success or -1 on failure."""
        if self.is_emtpy():
            return -1

        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)
            if filename in self.current:
                del self.current[filename]
                return 1

        cnstr = self.file_exists_constraint(filename)

        if self.is_sat(cnstr):
            self.state.add_constraints(cnstr)
            self._set_concrete_fname(filename, None)
            return 1

        return -1

    def delete_symbolic(self, filename: SymbString) -> int:
        """Delete a symbolic file and return 1 on success or -1 on failure."""
        if self.is_emtpy():
            return -1

        cnstr = self.file_exists_constraint(filename)

        if self.is_sat(cnstr):
            self.state.add_constraints(cnstr)
            self._set_symbolic_fname(filename, None)
            return 1

        return -1

    def delete_file(self, filename: str | SymbString) -> int | BV:
        """
        Delete a file.

        Returns `1` on success and `-1` on failure. When necessary, the
        required existence constraint is added to the path condition.
        """
        if isinstance(filename, str):
            return self.delete_concrete(filename)

        assert isinstance(filename, SymbString)
        return self.delete_symbolic(filename)

    def exists_concrete(self, filename: str) -> int | BV:
        """Return 1 if a concrete file exists, otherwise 0."""
        if self.is_emtpy():
            return 0

        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)
            if filename in self.current:
                file = self.current[filename]
                if file is not None:
                    return 1

        return self.search_exists(filename)

    def exists_symbolic(self, filename: SymbString) -> int | BV:
        """Return 1 if a symbolic file exists, otherwise 0."""
        if self.is_emtpy():
            return 0

        return self.search_exists(filename)

    def exists_file(self, filename: str | SymbString) -> int | BV:
        """
        Returns whether a file exists, possibly as a symbolic value.
        """
        if isinstance(filename, str):
            return self.exists_concrete(filename)

        assert isinstance(filename, SymbString)
        return self.exists_symbolic(filename)

    def FILE_from_fd_concrete(self, fd: int) -> int | BV:
        if self.is_emtpy():
            return -1

        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)
            for entries in self.current.values():
                if entries is not None:
                    file = self._get_first_file(entries)
                    if file.fd == fd:
                        return file.fp

        return self.get_fp_from_fd(fd)

    def FILE_from_fd_symbolic(self, fd: BV) -> int | BV:
        if self.is_emtpy():
            return -1

        return self.get_fp_from_fd(fd)

    def FILE_from_fd(self, fd: int | BV) -> int | BV:
        if isinstance(fd, int):
            return self.FILE_from_fd_concrete(fd)

        assert isinstance(fd, BV)
        return self.FILE_from_fd_symbolic(fd)

    def fd_from_FILE_concrete(self, fp: int) -> int | BV:
        if self.is_emtpy():
            return -1

        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)
            for entries in self.current.values():
                if entries is not None:
                    file = self._get_first_file(entries)
                    if file.fp == fp:
                        return file.fp

        return self.get_fd_from_fp(fp)

    def fd_from_FILE_symbolic(self, fp: BV) -> int | BV:
        if self.is_emtpy():
            return -1

        return self.get_fd_from_fp(fp)

    def fd_from_FILE(self, fp: int | BV) -> int | BV:
        if isinstance(fp, int):
            return self.fd_from_FILE_concrete(fp)

        assert isinstance(fp, BV)
        return self.fd_from_FILE_symbolic(fp)
