from abc import ABC, abstractmethod

from claripy.ast.bv import BV as BitVector

from .fs2 import SymbolicFS

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

    @abstractmethod
    def run(self):
        pass


class file_create(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr)
        status = self.fs.create_file(filename)
        print("Create file: ", status)
        return status


class file_delete(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr)
        status = self.fs.delete_file(filename)
        print("Delete file: ", status)
        return status


class file_exists(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr)
        status = self.fs.exists_file(filename)
        print("Exists file: ", status)
        return status


class file_open(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr)
        status = self.fs.open_file(filename)
        print("Open file: ", status)
        print(self.fs)
        return status


class file_close(FileSummary):
    def run(self, fd_bv):
        fd = self.load_numeric(fd_bv)
        status = self.fs.close_file(fd)
        print("Close file: ", status)
        print(self.fs)
        return status

class FILE_from_fd(FileSummary):
    def run(self, fd_bv):
        fd = self.load_numeric(fd_bv)
        status = self.fs.FILE_from_fd(fd)
        print(f"FILE*: {status:#x}")
        return status

class fd_from_FILE(FileSummary):
    def run(self, fp_bv):
        fp = self.load_numeric(fp_bv)
        status = self.fs.fd_from_FILE(fp)
        print("fd: ", status)
        return status
