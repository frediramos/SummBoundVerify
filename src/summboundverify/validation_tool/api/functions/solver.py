from claripy.ast.bv import BV as BitVector

from summboundverify.exceptions import DuplicateSymbolicVariableError

from ..summary import CSummary
from ..context import ValidationCTX

from .utils import get_name


class sym_var(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, length_bv: BitVector):
        length = self.state.solver.eval(length_bv)
        var = self.sym_var(length)
        var = var.zero_extend(self.state.arch.bits - length)
        self.ret(var)


class is_symbolic(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var):
        if self.is_symbolic(var):
            ret = 1
        else:
            ret = 0
        self.ret(ret)


class maximize(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var):
        value = self.maximize(var)
        self.ret(value)


class minimize(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var):
        value = self.minimize(var)
        self.ret(value)


class constraints(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self):
        print(self.state.solver.constraints)
        self.ret()


class assume(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, cnstr: BitVector):
        cnstr_id = self.state.solver.eval(cnstr)
        cnstr = self.ctx.CNSTR_MAP[cnstr_id]
        self.assume(cnstr)
        self.ret()


class is_certain(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, cnstr: BitVector):
        cnstr_id = self.state.solver.eval(cnstr)
        cnstr = self.ctx.CNSTR_MAP[cnstr_id]
        if self.is_certain(cnstr):
            ret = 1
        else:
            ret = 0
        self.ret(ret)


class is_sat(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, cnstr: BitVector):
        cnstr_id = self.state.solver.eval(cnstr)
        cnstr = self.ctx.CNSTR_MAP[cnstr_id]
        if self.is_sat(cnstr):
            ret = 1
        else:
            ret = 0
        self.ret(ret)


class _assert(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, cnstr: BitVector):
        if not self.is_symbolic(cnstr):
            cnstr_id = self.state.solver.eval(cnstr)
            cnstr = self.ctx.CNSTR_MAP[cnstr_id]
        self._assert(cnstr)
        self.ret()


class push_pc(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self):
        self.push_pc()
        self.ret()


class pop_pc(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self):
        self.pop_pc()
        self.ret()


class sym_var_named(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, name_addr, length_bv: BitVector):
        length = self.state.solver.eval(length_bv)

        name = get_name(self.state, name_addr)
        # A duplicate name would silently overwrite the earlier variable; report
        # it as a RunError so the caller can surface it (and the refinement loop
        # can act on it) instead of crashing with a bare AssertionError.
        if name in self.ctx.SYM_VARS.keys():
            raise DuplicateSymbolicVariableError(name)

        sym_var = self.sym_var(length, name)
        self.ctx.SYM_VARS[name] = [sym_var]

        sym_var = sym_var.zero_extend(self.state.arch.bits - length)

        self.ret(sym_var)


class sym_var_array(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, name_addr, index, length_bv: BitVector):

        length = self.state.solver.eval(length_bv)
        index = self.state.solver.eval(index)

        name = get_name(self.state, name_addr)
        bvname = f'{name}_{index}'

        sym_var = self.sym_var(length, bvname)

        if name not in self.ctx.SYM_VARS:
            self.ctx.SYM_VARS[name] = []

        self.ctx.SYM_VARS[name].append(sym_var)
        sym_var = sym_var.zero_extend(self.state.arch.bits - length)

        self.ret(sym_var)
