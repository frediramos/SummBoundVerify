import angr
import claripy

from copy import copy
from typing import Callable, Iterator
from dataclasses import dataclass, field

from angr import SimState
from cle.backends.externs.simdata.io_file import io_file_data_for_arch

from claripy import BVV, true, false
from claripy.ast import Bool, BV

from textwrap import indent

from ...utils import (
    SymbString,
    constraint,
    eq_strings,
    neq_strings
)


# ---------------------------------------------------------------------------
# Filenames
# ---------------------------------------------------------------------------

type ConcreteNameEntry = dict[str, bool]


@dataclass(frozen=True, slots=True)
class SymbolicNameEntry:

    filename: SymbString
    exists: bool


type FileNameEntry = ConcreteNameEntry | SymbolicNameEntry
type FileNames = list[FileNameEntry]


# ---------------------------------------------------------------------------
# File descriptors
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class File:
    size: int = 0
    bytes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FdEntry:
    filename: str | SymbString
    cond: Bool
    offset: int
    file: File

    def __repr__(self) -> str:
        return (
            "FdEntry(\n"
            f"\tfilename={self.filename!r},\n"
            f"\tcond={self.cond!r},\n"
            f"\toffset={self.offset},\n"
            f"\tfile={self.file!r}\n"
            ")"
        )


type FdEntries = tuple[str | SymbString, list[FdEntry]]


class SymbolicFS:
    """
    Model of a file system with concrete and symbolic file names and file descriptors.
    """

    def __init__(self, state: SimState) -> None:
        """Initialize an empty file system.

        File descriptor allocation starts at 3. Descriptors 0, 1, and 2
        are reserved for stdin, stdout, and stderr, respectively.
        """
        self.state = state

        self.fnames: FileNames = []
        self.fds: dict[int, FdEntries] = {}

        # Map of object id() values for correct cloning
        self.shared_files: dict[int, File | None] = {}

    def __repr__(self) -> str:
        sections = [
            self._repr_fnames(),
            self._repr_fds(),
            self._repr_shared_files(),
        ]

        return "SymbolicFS(\n" + "\n\n".join(sections) + "\n)"

    def _repr_fnames(self) -> str:
        lines = ["\tfnames:"]

        for entry in self.fnames:
            lines.append(f"\t\t{entry!r}")

        return "\n".join(lines)

    def _repr_fds(self) -> str:
        lines = ["\tfds:"]

        for fd, (filename, entries) in self.fds.items():
            lines.append(f"\t\tfd {fd} -> {filename!r}")
            lines.append("\t\t[")
            for entry in entries:
                lines.append(indent(repr(entry), "\t\t\t"))
            lines.append("\t\t[")
        return "\n".join(lines)

    def _repr_shared_files(self) -> str:
        lines = ["\tshared_files:"]

        for file_id, file in self.shared_files.items():
            lines.append(f"\t\t{file_id:#x} -> {file!r}")

        return "\n".join(lines)

    # ---------------------------------------------------------------------------
    # Cloning
    # ---------------------------------------------------------------------------

    def clone(self, state: SimState) -> "SymbolicFS":
        """
        Create an independent copy of the file system for an angr `state`.
        """
        fs = type(self)(state)
        fs.fnames = self._clone_fnames(self.fnames)
        fs.fds = self._clone_fds(self.fds)
        return fs

    # Filenames

    def _clone_fnames(self, entries: FileNames) -> FileNames:
        return [self._clone_fname_entry(e) for e in entries]

    def _clone_fname_entry(self, entry: FileNameEntry) -> FileNameEntry:
        if isinstance(entry, dict):
            return self._clone_concrete_fname_entry(entry)

        assert isinstance(entry, SymbolicNameEntry)
        return self._clone_symbolic_fname_entry(entry)

    def _clone_concrete_fname_entry(self, entry: ConcreteNameEntry) -> ConcreteNameEntry:
        return entry.copy()

    def _clone_symbolic_fname_entry(self, entry: SymbolicNameEntry) -> SymbolicNameEntry:
        return SymbolicNameEntry(copy(entry.filename), entry.exists)

    # File Descriptors

    def _clone_file(self, file: File) -> File:
        def clone(): return File(file.size, file.bytes.copy())

        id_ = id(file)
        if id_ in self.shared_files:
            value = self.shared_files.get(id_, None)
            if value is None:
                value = clone()
                self.shared_files[id_] = value
            return value

        return clone()

    def _clone_fd_entry(self, entry: FdEntry) -> FdEntry:
        return FdEntry(
            copy(entry.filename),
            entry.cond,
            entry.offset,
            self._clone_file(entry.file)
        )

    def _clone_fd_entries(self, entries: list[FdEntry]) -> list[FdEntry]:
        return [self._clone_fd_entry(e) for e in entries]

    def _clone_fds(self, fds: dict[int, FdEntries]) -> dict[int, FdEntries]:
        return {
            fd: (copy(name), self._clone_fd_entries(entry))
            for fd, (name, entry) in fds.items()
        }

    # ---------------------------------------------------------------------------
    # Utils
    # ---------------------------------------------------------------------------
    @property
    def current_fname(self):
        """Return the most recently added fname entry, or `None` if empty."""
        if self.is_fnames_emtpy():
            return None
        return self.fnames[-1]

    def new_fd(self) -> int:
        fd = 3
        while (True):
            if fd not in self.fds:
                return fd
            fd += 1

    def mark_shared(self, file: File):
        self.shared_files[id(file)] = None

    def is_concrete_fname(self, entry: FileNameEntry | None):
        """Return whether the file name `entry` contains concrete file names."""
        return isinstance(entry, dict)

    def is_sat(self, cnstr):
        """Return whether `cnstr` is satisfiable under the current path condition."""
        return self.state.solver.satisfiable(extra_constraints=(cnstr,))

    def is_fnames_emtpy(self):
        """Return whether the file system contains no entries."""
        return len(self.fnames) == 0

    def is_certain(self, cnstr):
        """Return whether `cnstr` is necessarily true under the current path condition."""
        neg_cnstr = claripy.Not(cnstr)
        return not self.state.solver.satisfiable(
            extra_constraints=(neg_cnstr,)
        )

    def bvv_int(self, value: int):
        """Create a bit-vector containing a C `int` value."""
        int_bits = self.state.arch.sizeof["int"]
        return BVV(value, int_bits)

    def search_open_concrete_name(self, filename: str) -> FdEntry | None:
        for (name, v) in self.fds.values():
            if isinstance(name, str) and name == filename:
                assert len(v) == 1
                entry = v[0]
                assert (name == entry.filename)
                return entry
        return None

    def search_open_symbolic_name(self, filename: str | SymbString) -> list[FdEntry] | None:
        for (name, v) in self.fds.values():
            if self.is_certain(eq_strings(name, filename)):
                return v
        return None

    def existing_fd_entries(self) -> list[FdEntry]:
        entries = []
        for fd in reversed(self.fds):
            _, fd_entries = self.fds[fd]
            for e in fd_entries:
                entries.append(e)
        return entries

    def fname_entry_to_list(self, entry: FileNameEntry):
        if isinstance(entry, dict):
            fnames = entry.items()
        else:
            assert isinstance(entry, SymbolicNameEntry)
            fnames = [(entry.filename, entry.exists)]
        return fnames

    def possible_fnames(self, filename: str | SymbString) -> list[str | SymbString]:
        fnames = []
        for f in reversed(self.fnames):
            names = self.fname_entry_to_list(f)
            fnames.extend(
                name for (name, exists) in names
                if exists and self.is_sat(eq_strings(name, filename))
            )
        return fnames

    # ---------------------------------------------------------------------------
    # Constraints
    # ---------------------------------------------------------------------------

    def file_exists_constraint(self, filename: str | SymbString) -> Bool:
        """Return a constraint indicating whether `filename` exists."""

        cases = []
        deleted = []

        for entry in reversed(self.fnames):
            fnames = self.fname_entry_to_list(entry)

            for name, exists in fnames:
                cond = eq_strings(filename, name)

                if not exists:
                    if self.is_certain(cond):
                        return false()
                    deleted.append(name)
                    continue

                if self.is_sat(cond):
                    cases.append(cond)

        eq = constraint(claripy.Or, *cases)
        neq = constraint(
            claripy.And,
            *[neq_strings(filename, d) for d in deleted]
        )
        condition = claripy.And(eq, neq)

        return condition

    def file_not_exists_constraint(self, filename: str | SymbString) -> Bool:
        """Return a constraint indicating that `filename` does not exist."""
        exists = self.file_exists_constraint(filename)
        return claripy.Not(exists)

    def file_exists_ite(self, filename: str | SymbString) -> int | BV:
        cases = []
        succ = 1
        err = 0
        def to_int(b): return self.bvv_int(succ) if b else self.bvv_int(err)

        for entry in reversed(self.fnames):
            if isinstance(entry, dict):
                fnames = [
                    (eq_strings(k, filename), to_int(v))
                    for k, v in entry.items()
                ]
            else:
                assert isinstance(entry, SymbolicNameEntry)
                fnames = [(
                    eq_strings(entry.filename, filename),
                    to_int(entry.exists)
                )]

            cases.extend(fnames)

        expr = claripy.ite_cases(cases, err)
        return expr

    # ---------------------------------------------------------------------------
    # Factories
    # ---------------------------------------------------------------------------

    def create_concrete_file(self, filename: str) -> int:
        """Create a concrete file."""

        def append_new():
            entry = {filename: True}
            self.fnames.append(entry)

        if self.is_fnames_emtpy():
            append_new()
            return 1

        if self.is_concrete_fname(self.current_fname):
            assert isinstance(self.current_fname, dict)
            if (
                filename in self.current_fname
                and self.current_fname[filename] is not None
            ):
                return -1

        # Creating the file requires the filename not to already exist.
        cnstr = self.file_not_exists_constraint(filename)

        if self.is_sat(cnstr):
            self.state.add_constraints(cnstr)
            append_new()
            return 1

        return -1

    def create_symbolic_file(self, filename: SymbString) -> int:
        """Create a symbolic file."""

        def append_new():
            entry = SymbolicNameEntry(filename, True)
            self.fnames.append(entry)

        if self.is_fnames_emtpy():
            append_new()
            return 1

        cnstr = self.file_not_exists_constraint(filename)

        if self.is_sat(cnstr):
            self.state.add_constraints(cnstr)
            append_new()
            return 1

        return -1

    def delete_concrete(self, filename: str) -> int:
        """Delete a concrete file and return 1 on success or -1 on failure."""

        def append_new():
            entry = {filename: False}
            self.fnames.append(entry)

        if self.is_fnames_emtpy():
            return -1

        if self.is_concrete_fname(self.current_fname):
            assert isinstance(self.current_fname, dict)
            if filename in self.current_fname:
                del self.current_fname[filename]
                return 1

        cnstr = self.file_exists_constraint(filename)

        if self.is_sat(cnstr):
            self.state.add_constraints(cnstr)
            append_new()
            return 1

        return -1

    def delete_symbolic(self, filename: SymbString) -> int:
        """Delete a symbolic file and return 1 on success or -1 on failure."""

        def append_new():
            entry = SymbolicNameEntry(filename, False)
            self.fnames.append(entry)

        if self.is_fnames_emtpy():
            return -1

        cnstr = self.file_exists_constraint(filename)

        if self.is_sat(cnstr):
            self.state.add_constraints(cnstr)
            append_new()
            return 1

        return -1

    def create_concrete_fd(self, filename: str) -> int:
        fd = self.new_fd()
        entry = self.search_open_concrete_name(filename)

        if entry is not None:
            entry.offset = 0
            self.mark_shared(entry.file)

        entry = FdEntry(filename, true(), 0, File())

        self.fds[fd] = (filename, [entry])
        return fd

    def create_symbolic_fd(self, filename: str | SymbString) -> int:
        fd = self.new_fd()
        entries = self.search_open_symbolic_name(filename)

        if entries is not None:
            for e in entries:
                e.offset = 0
                self.mark_shared(e.file)
        else:
            entries = []
            existing = self.existing_fd_entries()
            fnames = self.possible_fnames(filename)

            for e in existing:
                eq = eq_strings(filename, e.filename)
                cond = claripy.And(e.cond, eq)

                if self.is_sat(cond):
                    entry = FdEntry(e.filename, cond, 0, e.file)
                    self.mark_shared(e.file)
                    entries.append(entry)

            for name in fnames:
                cond = eq_strings(filename, name)
                entry = FdEntry(name, cond, 0, File())
                entries.append(entry)

        if len(entries) > 0:
            self.fds[fd] = (filename, entries)
            return fd

        return -1

    # ---------------------------------------------------------------------------
    # FS Functions
    # ---------------------------------------------------------------------------

    def create_file(self, filename: str | SymbString) -> int:
        """
        Create a file and return its file descriptor.

        Returns `-1` on failure. When necessary, the constraints required
        to establish that the file does not already exist are added to
        the current path condition.
        """
        if isinstance(filename, str):
            return self.create_concrete_file(filename)

        assert isinstance(filename, SymbString)
        return self.create_symbolic_file(filename)

    def delete_file(self, filename: str | SymbString) -> int:
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
        if self.is_fnames_emtpy():
            return 0

        if self.is_concrete_fname(self.current_fname):
            assert isinstance(self.current_fname, dict)
            if filename in self.current_fname:
                file = self.current_fname.get(filename, None)
                if file is not None:
                    return 1

        return self.file_exists_ite(filename)

    def exists_symbolic(self, filename: SymbString) -> int | BV:
        """Return 1 if a symbolic file exists, otherwise 0."""
        if self.is_fnames_emtpy():
            return 0

        return self.file_exists_ite(filename)

    def exists_file(self, filename: str | SymbString) -> int | BV:
        """
        Returns whether a file exists, possibly as a symbolic value.
        """
        if isinstance(filename, str):
            return self.exists_concrete(filename)

        assert isinstance(filename, SymbString)
        return self.exists_symbolic(filename)

    def open_concrete(self, filename: str) -> int:
        """Open a concrete file name and return its file descriptor."""
        if self.is_fnames_emtpy():
            return -1

        if self.is_concrete_fname(self.current_fname):
            assert isinstance(self.current_fname, dict)
            if filename in self.current_fname:
                exists = self.current_fname[filename]
                if exists:
                    return self.create_concrete_fd(filename)
                
        return self.create_symbolic_fd(filename)

    def open_symbolic(self, filename: SymbString) -> int:
        """Open a symbolic file name and return its file descriptor."""
        if self.is_fnames_emtpy():
            return -1

        ret = self.create_symbolic_fd(filename)
        return ret

    def open_file(self, filename: SymbString) -> int:
        """
        Open a file and returns a concrete descriptor.

        Returns `-1` if the file system is empty or the file cannot be found.
        """
        if not filename.is_symbolic():
            return self.open_concrete(str(filename))

        return self.open_symbolic(filename)
