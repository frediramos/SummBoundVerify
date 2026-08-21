from abc import ABC, abstractmethod

from claripy.ast.bv import BV as BitVector
from angr.state_plugins import SimStateGlobals

from .fs import SymbFileSystem

from ...summary import CSummary
from ...context import ValidationCTX


class FileSummary(CSummary, ABC):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    @property
    def fs(self) -> SymbFileSystem:
        plugin = self.state.globals
        assert isinstance(plugin, SimStateGlobals)

        fs = plugin["fs"]
        assert isinstance(fs, SymbFileSystem)

        if fs.state is not self.state:
            fs = fs.clone(self.state)
            plugin["fs"] = fs

        return fs

    def load_int(self, v: BitVector):
        if not self.is_symbolic(v):
            return self.state.solver.eval(v)
        return v

    @abstractmethod
    def run(self):
        pass


class file_create(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr)
        fd = self.fs.create_file(filename)
        print("Create fd: ", fd)
        return fd


class file_close(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr)
        status = self.fs.close_file(filename)
        print("Close status: ", status)
        return status


class file_open(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr)
        fd = self.fs.open_file(filename)
        print("Open fd: ", fd)
        return fd


class file_delete(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr)
        status = self.fs.delete_file(filename)
        print("Delete status: ", status)
        return status


class file_exists(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr)
        status = self.fs.exists_file(filename)
        print("Exists status: ", status)
        return status


class FILE_from_fd(FileSummary):
    def run(self, fd_: BitVector):
        fd = self.load_int(fd_)
        fp = self.fs.FILE_from_fd(fd)
        print("FILE pointer: ", fp)
        return fp


class fd_from_FILE(FileSummary):
    def run(self, fp_: BitVector):
        fp = self.load_int(fp_)
        fd = self.fs.fd_from_FILE(fp)
        print("File descriptor: ", fd)
        return fd
