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
        assert "fs" in plugin
        fs = plugin["fs"]
        assert isinstance(fs, SymbFileSystem)
        return fs

    @abstractmethod
    def run(self):
        pass


class file_create(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr)
        self.fs.create_file(filename)
