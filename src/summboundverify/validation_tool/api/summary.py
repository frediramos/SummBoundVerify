import claripy

from angr import SimProcedure

from claripy.ast.bv import BV as BitVector

from summboundverify.exceptions import (
    InvalidSymbolicVariableSizeError,
    InvalidArchVariableSizeError,
    UnsatConstraintError,
    ReportError,
)

from ..macros import SYM_VAR
from .context import ValidationCTX
from .utils import SymbString


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

    def load(self, addr, n=1):
        return self.state.memory.load(
            addr, n,
            endness=self.state.arch.memory_endness
        )

    def load_string(self, addr) -> SymbString:
        """
        Load a null-terminated string from memory.
        Can be symbolic.
        """
        i = 0
        chars = []
        endness = self.state.arch.memory_endness

        while True:
            byte: BitVector = self.state.memory.load(
                addr + i,
                1,
                endness=endness
            )

            if not self.is_symbolic(byte):
                code = self.state.solver.eval(byte)
                if code == 0:
                    break
                char = chr(code)
            else:
                char = byte

            chars.append(char)
            i += 1

        return SymbString(chars)

    def store(self, addr, value, n=1):
        self.state.memory.store(
            addr, value, n,
            endness=self.state.arch.memory_endness
        )

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

    def concretize(self, var):
        constraints = tuple(self.state.solver.constraints)
        concrete = self.state.solver.eval(var, extra_constraints=(constraints))
        return concrete

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

    def assert_constraint(self, cnstr):
        if not self.is_certain(cnstr):
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

    def report_error(self, filename: str, line: int, message: str):
        raise ReportError(filename, line, message)
