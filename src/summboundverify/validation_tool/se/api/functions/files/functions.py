from abc import ABC, abstractmethod

from claripy.ast.bv import BV as BitVector

from summboundverify.exceptions import SymbolicPointerError

from .fs import SymbolicFS

from ...utils import SymbString, called_by
from ...summary import CSummary
from ...context import ValidationCTX


class FileSummary(CSummary, ABC):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    @property
    def fs(self) -> SymbolicFS:
        plugin = self.state.fs
        assert isinstance(plugin, SymbolicFS)
        return plugin

    def load_numeric(self, v: BitVector):
        if not self.is_symbolic(v):
            return self.state.solver.eval(v)
        return v

    def load_string(self, addr, include_null: bool = False) -> SymbString:
        if self.is_symbolic(addr):
            caller = called_by(1)
            raise SymbolicPointerError(caller, addr)
        return super().load_string(addr, include_null)

    @abstractmethod
    def run(self):
        pass


class file_create(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr, include_null=True)
        status = self.fs.create_file(filename)
        print(self.fs)
        print(status)
        return status


class file_delete(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr, include_null=True)
        status = self.fs.delete_file(filename)
        return status


class file_exists(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr, include_null=True)
        status = self.fs.exists_file(filename)
        return status


class file_open(FileSummary):
    def run(self, filename_addr, flags_addr):
        filename = self.load_string(filename_addr, include_null=True)
        flags = self.load_string(flags_addr)
        status = self.fs.open_file(filename, flags)
        print(self.fs)
        print(status)
        return status


class file_close(FileSummary):
    def run(self, fd_bv):
        fd = self.load_numeric(fd_bv)
        status = self.fs.close_file(fd)
        return status


class file_write(FileSummary):
    def run(self, fd_bv, buffer_addr, count_bv):
        fd = self.load_numeric(fd_bv)
        buffer = self.load_string(buffer_addr, include_null=True)
        count = self.load_numeric(count_bv)
        n = self.fs.write_file(fd, buffer, count)
        return n


class file_read(FileSummary):
    def run(self, fd_bv, buffer, count_bv):
        fd = self.load_numeric(fd_bv)
        count = self.load_numeric(count_bv)
        n = self.fs.read_file(fd, buffer, count)
        return n


class FILE_from_fd(FileSummary):
    def run(self, fd_bv):
        fd = self.load_numeric(fd_bv)
        status = self.fs.FILE_from_fd(fd)
        return status


class fd_from_FILE(FileSummary):
    def run(self, fp_bv):
        fp = self.load_numeric(fp_bv)
        status = self.fs.fd_from_FILE(fp)
        return status


class file_offset(FileSummary):
    def run(self, fd_bv):
        fd = self.load_numeric(fd_bv)
        offset = self.fs.file_offset(fd)
        return offset


class file_set_offset(FileSummary):
    def run(self, fd_bv, offset_bv):
        fd = self.load_numeric(fd_bv)
        offset = self.load_numeric(offset_bv)
        offset = self.fs.file_set_offset(fd, offset)
        return offset


class file_size(FileSummary):
    def run(self, fd_bv):
        fd = self.load_numeric(fd_bv)
        offset = self.fs.file_size(fd)
        return offset


class file_set_size(FileSummary):
    def run(self, fd_bv, size_bv):
        fd = self.load_numeric(fd_bv)
        size = self.load_numeric(size_bv)
        size = self.fs.file_set_size(fd, size)
        return size


class file_dup(FileSummary):
    def run(self, fd_bv):
        fd1 = self.load_numeric(fd_bv)
        fd2 = self.fs.file_dup(fd1)
        return fd2


class file_dup2(FileSummary):
    def run(self, fd1_bv, fd2_bv):
        fd1 = self.load_numeric(fd1_bv)
        fd2 = self.load_numeric(fd2_bv)
        ret = self.fs.file_dup2(fd1, fd2)
        return ret


class file_mode(FileSummary):
    def run(self, fd_bv, mode_ptr_bv):
        fd = self.load_numeric(fd_bv)
        mode_ptr = self.load_numeric(mode_ptr_bv)
        status = self.fs.file_mode(fd, mode_ptr)
        return status


class file_set_mode(FileSummary):
    def run(self, fd_bv, mode_bv):
        fd = self.load_numeric(fd_bv)
        mode = self.load_numeric(mode_bv)
        status = self.fs.file_set_mode(fd, mode)
        return status


class file_flags(FileSummary):
    def run(self, fd_bv):
        fd = self.load_numeric(fd_bv)
        flags = self.fs.file_flags(fd)
        return flags


class fs_to_constraint(FileSummary):
    def run(self):
        c = self.fs.to_constraint()
        print(f"lifted fs: {c}")
