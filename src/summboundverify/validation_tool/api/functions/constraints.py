import claripy
from claripy.ast.bv import BV as BitVector

from ..summary import CSummary
from ..context import ValidationCTX


class _NOT_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, cnstr: BitVector):
        return_value = self.increment_CC()
        cnstr_id = self.state.solver.eval(cnstr)
        cnstr = self.ctx.CNSTR_MAP[cnstr_id]

        result = claripy.Not(cnstr)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _OR_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, cnstr1: BitVector, cnstr2: BitVector):
        return_value = self.increment_CC()

        cnstr_id1 = self.state.solver.eval(cnstr1)
        cnstr1 = self.ctx.CNSTR_MAP[cnstr_id1]

        cnstr_id2 = self.state.solver.eval(cnstr2)
        cnstr2 = self.ctx.CNSTR_MAP[cnstr_id2]

        result = claripy.Or(cnstr1, cnstr2)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _AND_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, cnstr1: BitVector, cnstr2: BitVector):
        return_value = self.increment_CC()

        cnstr_id1 = self.state.solver.eval(cnstr1)
        cnstr1 = self.ctx.CNSTR_MAP[cnstr_id1]

        cnstr_id2 = self.state.solver.eval(cnstr2)
        cnstr2 = self.ctx.CNSTR_MAP[cnstr_id2]

        result = claripy.And(cnstr1, cnstr2)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _EQ_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        result = var1 == var2
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _NEQ_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        result = var1 != var2
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _LT_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        result = var1.SLT(var2)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _LE_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        result = var1.SLE(var2)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _ULT_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        result = var1.ULT(var2)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _ULE_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        result = var1.ULE(var2)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _GT_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        result = var1.SGT(var2)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _GE_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        result = var1.SGE(var2)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _UGT_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        result = var1.UGT(var2)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _UGE_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        result = var1.UGE(var2)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _ITE_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, if_: BitVector, then_: BitVector, else_: BitVector):
        return_value = self.increment_CC()

        if_id = self.state.solver.eval(if_)
        then_id = self.state.solver.eval(then_)
        else_id = self.state.solver.eval(else_)

        cnstr_if = self.ctx.CNSTR_MAP[if_id]
        cnstr_then = self.ctx.CNSTR_MAP[then_id]
        cnstr_else = self.ctx.CNSTR_MAP[else_id]

        result = claripy.If(cnstr_if, cnstr_then, cnstr_else)

        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _ITE_VAR_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, if_: BitVector, sym1, sym2):

        if_id = self.state.solver.eval(if_)
        cnstr_if = self.ctx.CNSTR_MAP[if_id]

        result = claripy.If(cnstr_if, sym1, sym2)
        result = result.sign_extend(self.state.arch.bits - result.size())

        return result
