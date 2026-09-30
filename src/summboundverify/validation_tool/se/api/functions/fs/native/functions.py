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

        if filename.is_symbolic():
            return -1

        filename = str(filename).encode()

        # Check for an existing file
        if self.state.fs.get(filename) is not None:  # type: ignore
            return -1

        flags = claripy.BVV(os.O_WRONLY | os.O_CREAT, self.state.arch.bits)
        fd = self.state.posix.open(filename, flags)

        if not isinstance(fd, int) or fd < 0:
            return -1

        # Creating a file must not hold a descriptor so we close it
        self.state.posix.close(fd)
        return 1


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
