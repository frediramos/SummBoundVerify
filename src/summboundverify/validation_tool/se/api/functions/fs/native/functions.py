import os
import claripy

from abc import ABC, abstractmethod

from summboundverify.exceptions import NotImplementedApiError
from summboundverify.validation_tool.se.api import CSummary, ValidationCTX


class AngrFileSummary(CSummary, ABC):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    @abstractmethod
    def run(self):
        pass


class file_create(AngrFileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr)

        if any(self.state.solver.symbolic(c) for c in filename):
            return -1

        filename = b"".join(
            self.state.solver.eval(c, cast_to=bytes)  # type: ignore
            for c in filename
        )

        fd = self.state.posix.open(
            filename,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o644,
        )
        status = claripy.If(fd >= 0, 1, -1)
        return status


class file_delete(AngrFileSummary):
    def run(self, filename_addr):
        raise NotImplementedApiError("file_delete")


class file_exists(AngrFileSummary):
    def run(self, filename_addr):
        raise NotImplementedApiError("file_exists")


class file_open(AngrFileSummary):
    def run(self, filename_addr, flags_addr):
        raise NotImplementedApiError("file_open")


class file_close(AngrFileSummary):
    def run(self, fd_bv):
        raise NotImplementedApiError("file_close")


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
    def run(self, fd_bv, size_bv):
        raise NotImplementedApiError("file_set_size")


class file_dup(AngrFileSummary):
    def run(self, fd_bv):
        raise NotImplementedApiError("file_dup")


class file_dup2(AngrFileSummary):
    def run(self, fd1_bv, fd2_bv):
        raise NotImplementedApiError("file_dup2")


class file_mode(AngrFileSummary):
    def run(self, fd_bv, mode_ptr_bv):
        raise NotImplementedApiError("file_mode")


class file_set_mode(AngrFileSummary):
    def run(self, fd_bv, mode_bv):
        raise NotImplementedApiError("file_set_mode")


class file_flags(AngrFileSummary):
    def run(self, fd_bv):
        raise NotImplementedApiError("file_flags")


class fs_to_constraint(AngrFileSummary):
    def run(self):
        raise NotImplementedApiError("fs_to_constraint")
