import claripy

from abc import ABC, abstractmethod

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
