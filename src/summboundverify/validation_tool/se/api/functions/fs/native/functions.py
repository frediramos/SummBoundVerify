import stat
import angr
import claripy

from abc import ABC, abstractmethod


from angr.storage.file import Flags, SimFile
from angr.procedures.libc.fopen import mode_to_flag

from summboundverify.api import api
from summboundverify.validation_tool.se.api import CSummary, ValidationCTX
from summboundverify.exceptions import (
    InvalidModeError,
    InvalidPointerError,
    InvalidSizeError,
    NotImplementedApiError,
)


# angr's native file system, reached through the Symbolic Reflection API.
#
# The test suite exists to expose bugs in the file systems of symbolic
# execution tools, so each function runs the same code as the angr summary
# it stands for (fopen, close, access, ...) and does not correct it.
#
#   BUG #N        A known angr bug, numbered as in docs/notes/angr.md. The
#                 tests are what should catch it.
#   FAIR CHANCE   A place where angr is set up to behave like a real file
#                 system, where it otherwise would not by default.


class AngrFileSummary(CSummary, ABC):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    @abstractmethod
    def run(self):
        pass

    def load_concrete(self, value_bv, error) -> int:
        """The concrete value of `value_bv`, which the API requires: raises
        `error` if it has more than one."""
        try:
            return self.state.solver.eval_one(value_bv, cast_to=int)
        except Exception:
            raise error(api(type(self).__name__), value_bv)

    def load_size(self, size_bv) -> int:
        return self.load_concrete(size_bv, InvalidSizeError)

    def load_mode(self, mode_bv) -> int:
        return self.load_concrete(mode_bv, InvalidModeError)

    def load_path(self, addr) -> bytes:
        """The string at `addr`, loaded as angr's fopen summary loads names.

        BUG #5: a symbolic string is concretized to one of its values,
        without constraining it. The string stays symbolic, so each call
        may choose a different value.
        """
        strlen = angr.SIM_PROCEDURES["libc"]["strlen"]
        length = self.inline_call(strlen, addr)
        
        expr = self.state.memory.load(
            addr,
            length.max_null_index,
            endness="Iend_BE"
        )
        
        return self.state.solver.eval(expr, cast_to=bytes)

    def load_pointer(self, ptr_bv) -> int:
        return self.load_concrete(ptr_bv, InvalidPointerError)

    # BUG #13: angr keeps no file modes, so the API keeps them itself, in the
    # state's globals, keyed by file name. Not on the SimFile: SimFile.copy
    # drops attributes it does not know, so they would be lost when the state
    # splits. Nothing in angr reads them.
    FILE_MODES = "file_modes"

    def recorded_mode(self, simfile: SimFile) -> int | None:
        return self.state.globals.get(self.FILE_MODES, {}).get(simfile.name)  # type: ignore

    def record_mode(self, simfile: SimFile, mode: int):
        # Replace the dict rather than update it: the globals are copied
        # shallowly when the state splits, so a dict updated in place would
        # be shared by every path
        modes = dict(self.state.globals.get(self.FILE_MODES, {}))  # type: ignore
        modes[simfile.name] = mode & 0o7777
        self.state.globals[self.FILE_MODES] = modes  # type: ignore

    def get_simfile(self, fd_bv) -> SimFile | None:
        """The file open on `fd_bv`, or None if it is not an open file."""
        simfd = self.state.posix.get_fd(fd_bv)
        if simfd is None or not isinstance(simfd.file, SimFile):
            return None
        return simfd.file


class file_create(AngrFileSummary):
    """Create the file `name`, as open(name, O_WRONLY | O_CREAT | O_EXCL, 0644)
    followed by close.

    angr has no summary for creating a file, so this uses posix.open, the
    function angr's open and fopen summaries are built on. The name is
    loaded as fopen loads it (see load_path).
    """

    def run(self, filename_addr):
        filename = self.load_path(filename_addr)

        # BUG #4: posix.open ignores O_EXCL, so the API's "fail if the file
        # exists" is checked here
        if self.state.fs.get(filename) is not None:  # type: ignore
            return -1

        flags = claripy.BVV(Flags.O_WRONLY | Flags.O_CREAT, self.state.arch.bits)
        fd = self.state.posix.open(filename, flags)

        if not isinstance(fd, int) or fd < 0:
            return -1

        # FAIR CHANCE: posix.open creates files without an end (BUG #8).
        # Give this one an end of file, as a regular file has.
        simfile = self.state.posix.get_fd(fd).file  # type: ignore
        simfile.has_end = True

        # BUG #13: posix.open ignores the mode, so the API records it
        self.record_mode(simfile, 0o644)

        # Creating a file must not hold a descriptor
        self.state.posix.close(fd)
        return 1


class file_delete(AngrFileSummary):
    def run(self, filename_addr):
        raise NotImplementedApiError("file_delete")


class file_exists(AngrFileSummary):
    """access(name, F_OK), as angr's access syscall summary, returning 1 if
    the file exists and 0 if not.

    BUG #5: a symbolic name is concretized (see load_path), so the result
    is for one arbitrary name. __assume(__file_exists(name) == 1) does not
    constrain a symbolic name to the files that exist; it is unsatisfiable
    whenever the chosen name does not exist.

    angr's libc access summary ignores the file system (bug #11 in
    angr.md); the syscall summary, copied here, checks it.
    """

    def run(self, filename_addr):
        path = self.load_path(filename_addr)
        if self.state.fs.get(path) is None:  # type: ignore
            return 0
        return 1


class file_open(AngrFileSummary):
    """fopen(name, mode), returning the descriptor instead of a FILE *.

    The same steps as angr's fopen summary, without the FILE struct.
    """

    def run(self, filename_addr, flags_addr):
        # BUG #5: a symbolic name or mode is concretized (see load_path)
        path = self.load_path(filename_addr)
        mode = self.load_path(flags_addr)

        # BUG #1: mode_to_flag leaves O_TRUNC out of "w" and "w+"
        #
        # posix.open then:
        #   BUG #2: ignores O_TRUNC, so an existing file is never truncated
        #   BUG #3: creates a missing file opened for writing, without O_CREAT
        #   BUG #9: does not create a missing file opened read-only, with O_CREAT
        #   BUG #4: ignores O_EXCL
        #
        # FAIR CHANCE: a missing file opened read-only fails, because the
        # engine turns off ALL_FILES_EXIST on this file system. With it,
        # posix.open invents any missing file.
        fd = self.state.posix.open(path, mode_to_flag(mode))
        return fd


class file_close(AngrFileSummary):
    """close(fd), as angr's close summary."""

    def run(self, fd_bv):
        if self.state.posix.close(fd_bv):
            return 0
        return -1


class file_write(AngrFileSummary):
    def run(self, fd_bv, buffer_addr, count_bv):
        raise NotImplementedApiError("file_write")


class file_read(AngrFileSummary):
    def run(self, fd_bv, buffer, count_bv):
        raise NotImplementedApiError("file_read")


class FILE_from_fd(AngrFileSummary):
    def run(self, fd_bv):
        raise NotImplementedApiError("FILE_from_fd")


class fd_from_FILE(AngrFileSummary):
    def run(self, fp_bv):
        raise NotImplementedApiError("fd_from_FILE")


class file_offset(AngrFileSummary):
    def run(self, fd_bv):
        raise NotImplementedApiError("file_offset")


class file_set_offset(AngrFileSummary):
    def run(self, fd_bv, offset_bv):
        raise NotImplementedApiError("file_set_offset")


class file_size(AngrFileSummary):
    def run(self, fd_bv):
        raise NotImplementedApiError("file_size")


class file_set_size(AngrFileSummary):
    """ftruncate(fd, size), returning the new size.

    BUG #7: angr has no truncate or ftruncate summary, and SimFile has no
    way to resize a file. It keeps the size in the private _size, which
    SimFile.write sets to grow a file, so this sets it too. Bytes past the
    old size are unconstrained.
    """

    def run(self, fd_bv, size_bv):
        size = self.load_size(size_bv)

        simfile = self.get_simfile(fd_bv)
        if simfile is None:
            return -1

        # BUG #8: on a file without an end, the size is only a lower bound:
        # reads past it still succeed and grow the file
        simfile._size = claripy.BVV(size, self.state.arch.bits)
        return size


class file_dup(AngrFileSummary):
    def run(self, fd_bv):
        raise NotImplementedApiError("file_dup")


class file_dup2(AngrFileSummary):
    def run(self, fd1_bv, fd2_bv):
        raise NotImplementedApiError("file_dup2")


class file_mode(AngrFileSummary):
    """fstat(fd), storing st_mode in *mode; returns 1 or -1.

    BUG #13: angr keeps no file modes. For a file whose mode the API
    recorded (__file_create, __file_set_mode), this is that mode, as a
    regular file. For any other file, e.g. one angr's open created, it is
    what angr's own fstat reports (posix.fstat): a new symbolic st_mode.
    """

    def run(self, fd_bv, mode_ptr_bv):
        mode_ptr = self.load_pointer(mode_ptr_bv)

        simfile = self.get_simfile(fd_bv)
        if simfile is None:
            return -1

        recorded = self.recorded_mode(simfile)
        if recorded is not None:
            mode = claripy.BVV(stat.S_IFREG | recorded, 32)
        else:
            mode = self.state.posix.fstat(fd_bv).st_mode

        self.state.memory.store(mode_ptr, mode, endness=self.state.arch.memory_endness)
        return 1


class file_set_mode(AngrFileSummary):
    """fchmod(fd, mode), returning 1 or -1.

    BUG #13: angr has no file permissions: a SimFile keeps no mode, and open
    never checks one. Nor can a program read a mode back: libc's fstat has
    no summary, so it returns an unconstrained value and leaves the stat
    buffer as it was. So this only records the mode (see record_mode), for
    __file_mode; nothing in angr reads it. A test that sets 0444 and then
    opens the file for writing sees the open succeed.
    """

    def run(self, fd_bv, mode_bv):
        mode = self.load_mode(mode_bv)

        simfile = self.get_simfile(fd_bv)
        if simfile is None:
            return -1

        self.record_mode(simfile, mode)
        return 1


class file_flags(AngrFileSummary):
    """fcntl(fd, F_GETFL): the open flags angr keeps on the descriptor.

    BUG #1: for a descriptor from __file_open, these are mode_to_flag's
    flags, so "w" and "w+" lack O_TRUNC.
    """

    def run(self, fd_bv):
        simfd = self.state.posix.get_fd(fd_bv)
        if simfd is None:
            return -1
        return simfd.flags


class fs_to_constraint(AngrFileSummary):
    def run(self):
        raise NotImplementedApiError("fs_to_constraint")
