import sys
import claripy
from angr import SimProcedure

from ..macros import SYM_VAR
from . context import ValidationCTX


class UnsatException(Exception):
    pass


class CSummary(SimProcedure):

    def __init__(self, ctx: ValidationCTX):
        super().__init__()
        self.ctx = ctx

    def increment_CC(self):
        current = self.ctx.CNSTR_COUNTER
        self.ctx.CNSTR_COUNTER += 1
        return current

    def stop_exec(self, msg: str):
        error = '[!] Execution Terminated [!] +' \
            f'Reason: {msg}'
        sys.exit(error)

    # Symbolic State
    # -----------------------------------------------------------------------------------

    def Load(self, addr):
        return self.state.memory.load(addr, 1, endness=self.state.arch.memory_endness)

    def sym_var(self, length):
        if length % 8 != 0:
            msg = f'Failed \'{self.sym_var.__name__}\' with size: {length} | ' + \
                'Size in bits must be divisible by 8'
            self.stop_exec(msg)

        sym_var = self.state.solver.BVS(SYM_VAR, length)
        sym_var = sym_var.zero_extend(self.state.arch.bits - length)
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
            raise UnsatException(f'Unsat cnstr in \'assume\': {cnstr}')
        self.state.solver.add(cnstr)

    def is_certain(self, cnstr):
        neg_cnstr = claripy.Not(cnstr)
        return not self.state.solver.satisfiable(extra_constraints=(neg_cnstr,))

    def is_sat(self, cnstr):
        return self.state.solver.satisfiable(extra_constraints=(cnstr,))

    def _assert(self, cnstr):
        if not self.state.solver.satisfiable(extra_constraints=(cnstr,)):
            raise UnsatException(f'Unsat cnstr in \'_assert\': {cnstr}')

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

        c = self.state.globals['pc_stack'].pop() # type: ignore
        self.state.solver.reload_solver(c)
