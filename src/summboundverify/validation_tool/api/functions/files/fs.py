import angr
import claripy

from copy import copy
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


type ConcrFileEntry = dict[str, File | None]


@dataclass(frozen=True, slots=True)
class SymbFileEntry:
    """
    A file whose name is represented by a symbolic string.

    A `None` file represents a deleted file.
    A `File` with `fd = -1` represents a closed file.
    """

    filename: SymbString
    file: File | None


type FileEntry = ConcrFileEntry | SymbFileEntry


class SymbFileSystem:
    """Model of a file system with concrete and symbolic file names."""

    def __init__(self, state: SimState) -> None:
        """Initialize an empty file system.

        File descriptor allocation starts at 3. Descriptors 0, 1, and 2
        are reserved for stdin, stdout, and stderr, respectively.
        """
        self.state = state
        self.fd = 3
        self.entries: list[FileEntry] = []

    def clone(self, state: SimState) -> "SymbFileSystem":
        """
        Create an independent copy of the file system for `state`.
        """
        fs = type(self)(state)
        fs.fd = self.fd
        fs.entries = [
            dict(entry) if isinstance(entry, dict)
            else SymbFileEntry(copy(entry.filename), copy(entry.file))
            for entry in self.entries
        ]
        return fs

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
        return isinstance(entry, SymbFileEntry)

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

    def add(self, entry: FileEntry):
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

    def _create_file(self, fd: int | None = None):
        if fd is None:
            fd = self.incr_fd()
        fp = self._create_fp(fd)
        file = File(fd=fd, fp=fp)
        return file

    def _closed_file(self) -> File:
        """Return a file object representing a closed file."""
        file = self._create_file(-1)
        return file

    def file_exists_constraint(self, filename: str | SymbString) -> Bool:
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
                if file is None:  # Deleted file
                    continue

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

    def search_by_filename(
        self,
        name: str | SymbString
    ) -> list[tuple[Bool, File | None]]:
        """
        Return possible files matching `name` and their conditions.
        """
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

                if self.is_certain(condition):
                    cases.append((true(), file))
                    return cases

                cases.append((condition, file))

        return cases

    def search_fd(self, name: str | SymbString) -> BV:
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

    def search_by_fd(
        self,
        fd: int | BV
    ) -> list[tuple[Bool, File | None]]:
        """
        Return possible files matching `fd` and their conditions.
        """
        cases = []
        deleted = []

        for entry in reversed(self.entries):
            if self.is_concrete(entry):
                assert isinstance(entry, dict)
                files = entry.items()
            else:
                assert isinstance(entry, SymbFileEntry)
                files = [(entry.filename, entry.file)]

            for filename, file in files:
                if file is None or file.fd == -1:
                    deleted.append(filename)
                    continue

                neq = constraint(
                    claripy.And,
                    *[neq_strings(filename, d) for d in deleted]
                )

                condition = claripy.And((fd == file.fd), neq)

                if self.is_certain(condition):
                    cases.append((true(), file))
                    return cases

                cases.append((condition, file))

        return cases

    def _set_concrete(self, filename: str, file: File | None):
        """Add a concrete file entry, reusing the current concrete entry when possible."""
        if self.is_concrete(self.current):
            assert isinstance(self.current, dict)
            self.current[filename] = file
        else:
            self.add({filename: file})

    def _set_symbolic(self, filename: SymbString, file: File | None):
        """Add a symbolic file entry."""
        entry = SymbFileEntry(filename, file)
        self.add(entry)

    def _create_concrete(self, filename: str) -> int:
        file = self._create_file()
        fd = file.fd
        self._set_concrete(filename, file)
        return fd

    def _create_symbolic(self, filename: SymbString):
        file = self._create_file()
        fd = file.fd
        self._set_symbolic(filename, file)
        return fd

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
            if (
                filename in self.current
                and self.current[filename] is not None
            ):
                self.current[filename] = self._closed_file()

        cnstr = self.file_exists_constraint(filename)

        if self.is_sat(cnstr):
            self.state.add_constraints(cnstr)
            self._set_concrete(filename, self._closed_file())
            return 1

        return -1

    def close_symbolic(self, filename: SymbString) -> int:
        """Close a symbolic file and return 1 on success or -1 on failure."""
        if self.is_emtpy():
            return -1

        cnstr = self.file_exists_constraint(filename)

        if self.is_sat(cnstr):
            self.state.add_constraints(cnstr)
            self._set_symbolic(filename, self._closed_file())
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
                file = self.current[filename]
                if file is not None:
                    return file.fd

        return self.search_fd(filename)

    def open_symbolic(self, filename: SymbString) -> int | BV:
        """Open a symbolic file name and return its file descriptor."""
        if self.is_emtpy():
            return -1

        return self.search_fd(filename)

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
            self._set_concrete(filename, None)
            return 1

        return -1

    def delete_symbolic(self, filename: SymbString) -> int:
        """Delete a symbolic file and return 1 on success or -1 on failure."""
        if self.is_emtpy():
            return -1

        cnstr = self.file_exists_constraint(filename)

        if self.is_sat(cnstr):
            self.state.add_constraints(cnstr)
            self._set_symbolic(filename, None)
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
