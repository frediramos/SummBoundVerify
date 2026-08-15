import claripy

from claripy import ClaripyError
from claripy.ast.bv import BV as BitVector

from summboundverify.exceptions import (
    ClaripyConstraintError
)

from ..summary import CSummary
from ..context import ValidationCTX

from ..utils import constraint


class _NOT_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, cnstr: BitVector):
        return_value = self.increment_CC()
        cnstr_id = self.state.solver.eval(cnstr)
        cnstr = self.ctx.CNSTR_MAP[cnstr_id]

        result = constraint(
            claripy.Not,
            cnstr,
            caller=_NOT_.__name__
        )

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

        result = constraint(
            claripy.Or,
            cnstr1,
            cnstr2,
            caller=_OR_.__name__
        )

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

        result = constraint(
            claripy.And,
            cnstr1,
            cnstr2,
            caller=_AND_.__name__
        )

        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _EQ_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        def _EQ_(): return var1 == var2
        result = constraint(_EQ_, caller=_EQ_.__name__)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _NEQ_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        def _NEQ_(): return var1 != var2
        result = constraint(_NEQ_, caller=_NEQ_.__name__)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _LT_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        def _LT_(): return var1.SLT(var2)
        result = constraint(_LT_, caller=_LT_.__name__)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _LE_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        def _LE_(): return var1.SLE(var2)
        result = constraint(_LE_, caller=_LE_.__name__)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _ULT_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        def _ULT_(): return var1.ULT(var2)
        result = constraint(_ULT_, caller=_ULT_.__name__)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _ULE_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        def _ULE_(): return var1.ULE(var2)
        result = constraint(_ULE_, caller=_ULE_.__name__)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _GT_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        def _GT_(): return var1.SGT(var2)
        result = constraint(_GT_, caller=_GT_.__name__)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _GE_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        def _GE_(): return var1.SGE(var2)
        result = constraint(_GE_, caller=_GE_.__name__)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _UGT_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        def _UGT_(): return var1.UGT(var2)
        result = constraint(_UGT_, caller=_UGT_.__name__)
        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _UGE_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, var1, var2):
        return_value = self.increment_CC()
        def _UGE_(): return var1.UGE(var2)
        result = constraint(_UGE_, caller=_UGE_.__name__)
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

        result = constraint(
            claripy.If,
            cnstr_if,
            cnstr_then,
            cnstr_else,
            caller=_ITE_.__name__
        )

        self.ctx.CNSTR_MAP.append(result)
        return return_value


class _ITE_VAR_(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, if_: BitVector, sym1, sym2):

        if_id = self.state.solver.eval(if_)
        cnstr_if = self.ctx.CNSTR_MAP[if_id]

        try:
            result = claripy.If(cnstr_if, sym1, sym2)
            result = result.sign_extend(self.state.arch.bits - result.size())
        except ClaripyError as e:
            raise ClaripyConstraintError("If", e, caller=_ITE_VAR_.__name__)

        return result
