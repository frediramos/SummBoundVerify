import claripy
from angr import SimProcedure

from summboundverify.exceptions import (
    InvalidSymbolicVariableSizeError,
    InvalidArchVariableSizeError,
    UnsatConstraintError
)

from ..macros import SYM_VAR
from . context import ValidationCTX


class CSummary(SimProcedure):

    def __init__(self, ctx: ValidationCTX):
        super().__init__()
        self.ctx = ctx

    def increment_CC(self):
        current = self.ctx.CNSTR_COUNTER
        self.ctx.CNSTR_COUNTER += 1
        return current

    # Symbolic State
    # -----------------------------------------------------------------------------------

    def Load(self, addr):
        return self.state.memory.load(addr, 1, endness=self.state.arch.memory_endness)

    def sym_var(self, length, name=None):
        arch_bits = self.state.arch.bits
        explicit_name = True

        if length > arch_bits:
            raise InvalidArchVariableSizeError(length, arch_bits)

        if length % 8 != 0:
            raise InvalidSymbolicVariableSizeError(length)

        if not name:
            name = SYM_VAR
            explicit_name = False

        sym_var = self.state.solver.BVS(
            name, length, explicit_name=explicit_name)
        return sym_var

    def is_symbolic(self, var):
        return self.state.solver.symbolic(var)

    def maximize(self, var):
        constraints = tuple(self.state.solver.constraints)
        max_val = self.state.solver.max(var, extra_constraints=(constraints))
        return max_val

    def minimize(self, var):
        constraints = tuple(self.state.solver.constraints)
        min_val = self.state.solver.min(var, extra_constraints=(constraints))
        return min_val

    def assume(self, cnstr):
        if not self.state.solver.satisfiable(extra_constraints=(cnstr,)):
            raise UnsatConstraintError("assume", cnstr)
        self.state.solver.add(cnstr)

    def is_certain(self, cnstr):
        neg_cnstr = claripy.Not(cnstr)
        return not self.state.solver.satisfiable(extra_constraints=(neg_cnstr,))

    def is_sat(self, cnstr):
        return self.state.solver.satisfiable(extra_constraints=(cnstr,))

    def _assert(self, cnstr):
        if not self.state.solver.satisfiable(extra_constraints=(cnstr,)):
            raise UnsatConstraintError("_assert", cnstr)

    def push_pc(self):
        c = self.state.solver._solver.constraints

        if 'pc_stack' not in self.state.globals.keys():  # type: ignore
            self.state.globals['pc_stack'] = []  # type: ignore

        self.state.globals['pc_stack'].append(c)  # type: ignore

    def pop_pc(self):
        assert (
            'pc_stack' in self.state.globals.keys() and   # type: ignore
            len(self.state.globals['pc_stack']) > 0  # type: ignore
        )

        c = self.state.globals['pc_stack'].pop()  # type: ignore
        self.state.solver.reload_solver(c)
