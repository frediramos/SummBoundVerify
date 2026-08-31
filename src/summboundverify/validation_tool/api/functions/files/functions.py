from abc import ABC, abstractmethod

from claripy.ast.bv import BV as BitVector
from angr.state_plugins import SimStateGlobals

from .fs2 import SymbolicFS

from ...summary import CSummary
from ...context import ValidationCTX


class FileSummary(CSummary, ABC):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    @property
    def fs(self) -> SymbolicFS:
        plugin = self.state.globals
        assert isinstance(plugin, SimStateGlobals)

        fs = plugin["fs"]
        assert isinstance(fs, SymbolicFS)

        if fs.state is not self.state:
            fs = fs.clone(self.state)
            plugin["fs"] = fs

        return fs

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
