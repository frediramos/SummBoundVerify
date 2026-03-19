import sys
import claripy

from angr import SimProcedure
from collections import OrderedDict

from .constraints import CNSTR_MAP
from ..macros import SYM_VAR
from .utils import *


class UnsatException(Exception):
    pass


class CSummary(SimProcedure):

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

    def sym_var_float(self, length):
        if length % 8 != 0:
            msg = f'Failed \'{self.sym_var_float.__name__}\' with size: {length} | ' + \
                'Size in bits must be divisible by 8'
            self.stop_exec(msg)

        assert length == 32 or length == 64
        name = f'{SYM_VAR}_float'
        if length == 32:
            sym_var_fp = self.state.solver.FPS(
                name, self.state.solver.fp.FSORT_FLOAT)
        else:
            sym_var_fp = self.state.solver.FPS(
                name, self.state.solver.fp.FSORT_DOUBLE)

        self.all_variables = list(self.all_variables)
        self.all_variables.append(sym_var_fp)

        sym_var_fp = sym_var_fp.zero_extend(self.state.arch.bits - length)
        return sym_var_fp

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
        if 'pc_stack' not in self.state.globals.keys():
            self.state.globals['pc_stack'] = []

        self.state.globals['pc_stack'].append(c)

    def pop_pc(self):
        assert 'pc_stack' in self.state.globals.keys() and \
            len(self.state.globals['pc_stack'])

        c = self.state.globals['pc_stack'].pop()
        self.state.solver.reload_solver(c)


class sym_var(CSummary):
    def run(self, length):
        length = self.state.solver.eval(length)
        var = self.sym_var(length)
        try:
            self.ret(var)
        except Exception as e:
            print(e)


class sym_var_float(CSummary):
    def run(self, length):
        length = self.state.solver.eval(length)
        var = self.sym_var_float(length)
        try:
            self.ret(var)
        except Exception as e:
            print(e)


class is_symbolic(CSummary):
    def run(self, var):
        if self.is_symbolic(var):
            ret = 1
        else:
            ret = 0
        self.ret(ret)


class maximize(CSummary):
    def run(self, var):
        value = self.maximize(var)
        self.ret(value)


class minimize(CSummary):
    def run(self, var):
        value = self.minimize(var)
        self.ret(value)


class constraints(CSummary):
    def run(self):
        print(self.state.solver.constraints)
        self.ret()


class assume(CSummary):
    def run(self, cnstr):
        cnstr_id = self.state.solver.eval(cnstr)
        cnstr = CNSTR_MAP[cnstr_id]
        self.assume(cnstr)
        self.ret()


class is_certain(CSummary):
    def run(self, cnstr):
        cnstr_id = self.state.solver.eval(cnstr)
        cnstr = CNSTR_MAP[cnstr_id]
        if self.is_certain(cnstr):
            ret = 1
        else:
            ret = 0
        self.ret(ret)


class is_sat(CSummary):
    def run(self, cnstr):
        cnstr_id = self.state.solver.eval(cnstr)
        cnstr = CNSTR_MAP[cnstr_id]
        if self.is_sat(cnstr):
            ret = 1
        else:
            ret = 0
        self.ret(ret)


class _assert(CSummary):
    def run(self, cnstr):
        cnstr_id = self.state.solver.eval(cnstr)
        cnstr = CNSTR_MAP[cnstr_id]
        self._assert(cnstr)
        self.ret()


class push_pc(CSummary):
    def run(self):
        self.push_pc()
        self.ret()


class pop_pc(CSummary):
    def run(self):
        self.pop_pc()
        self.ret()


# Symbolic variables generated
SYM_VARS = OrderedDict()


class sym_var_named(SimProcedure):

    def run(self, name_addr, length):

        length = self.state.solver.eval(length)
        assert length % 8 == 0, "[!] Size in bits must be divisible by 8"

        name = get_name(self.state, name_addr)
        assert (name not in SYM_VARS.keys())

        sym_var = self.state.solver.BVS(name, length, explicit_name=True)
        SYM_VARS[name] = [sym_var]

        sym_var = sym_var.zero_extend(self.state.arch.bits - length)

        try:
            self.ret(sym_var)
        except Exception as e:
            print(e)


class sym_var_array(SimProcedure):

    def run(self, name_addr, index, length):

        length = self.state.solver.eval(length)
        assert length % 8 == 0, "[!] Size in bits must be divisible by 8"

        index = self.state.solver.eval(index)

        name = get_name(self.state, name_addr)
        bvname = f'{name}_{index}'

        sym_var = self.state.solver.BVS(bvname, length, explicit_name=True)

        if name not in SYM_VARS:
            SYM_VARS[name] = []

        SYM_VARS[name].append(sym_var)

        sym_var = sym_var.zero_extend(self.state.arch.bits - length)

        try:
            self.ret(sym_var)
        except Exception as e:
            print(e)


summaries = [
    sym_var,
    sym_var_named,
    sym_var_array,
    sym_var_float,
    is_symbolic,
    maximize,
    minimize,
    constraints,
    assume,
    is_certain,
    is_sat,
    _assert,
    push_pc,
    pop_pc
]
