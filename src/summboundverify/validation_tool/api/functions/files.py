import claripy

from abc import ABC, abstractmethod

from claripy.ast.bv import BV as BitVector
from angr.state_plugins.sim_action_object import SimActionObject

from ..summary import CSummary
from ..context import ValidationCTX


class FileSummary(CSummary, ABC):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    @abstractmethod
    def run(self):
        pass
