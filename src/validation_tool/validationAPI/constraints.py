from angr import SimProcedure

# Constraints
# ------------------------------------------------------
CNSTR_COUNTER = 0
CNSTR_MAP = []


class CSummary(SimProcedure):

    def _incrementCC(self):
        global CNSTR_COUNTER
        current = CNSTR_COUNTER
        CNSTR_COUNTER += 1
        return current


class _NOT_(CSummary):
    def run(self, cnstr):
        return_value = self._incrementCC()
        cnstr_id = self.state.solver.eval(cnstr)
        cnstr = CNSTR_MAP[cnstr_id]

        result = self.state.solver.Not(cnstr)
        CNSTR_MAP.append(result)
        return return_value


class _OR_(CSummary):
    def run(self, cnstr1, cnstr2):
        return_value = self._incrementCC()

        cnstr_id1 = self.state.solver.eval(cnstr1)
        cnstr1 = CNSTR_MAP[cnstr_id1]

        cnstr_id2 = self.state.solver.eval(cnstr2)
        cnstr2 = CNSTR_MAP[cnstr_id2]

        result = self.state.solver.Or(cnstr1, cnstr2)
        CNSTR_MAP.append(result)
        return return_value


class _AND_(CSummary):
    def run(self, cnstr1, cnstr2):
        return_value = self._incrementCC()

        cnstr_id1 = self.state.solver.eval(cnstr1)
        cnstr1 = CNSTR_MAP[cnstr_id1]

        cnstr_id2 = self.state.solver.eval(cnstr2)
        cnstr2 = CNSTR_MAP[cnstr_id2]

        result = self.state.solver.And(cnstr1, cnstr2)
        CNSTR_MAP.append(result)
        return return_value


class _EQ_(CSummary):
    def run(self, var1, var2):
        return_value = self._incrementCC()
        result = var1 == var2
        CNSTR_MAP.append(result)
        return return_value


class _NEQ_(CSummary):
    def run(self, var1, var2):
        return_value = self._incrementCC()
        result = var1 != var2
        CNSTR_MAP.append(result)
        return return_value


class _LT_(CSummary):
    def run(self, var1, var2):
        return_value = self._incrementCC()
        result = var1.SLT(var2)
        CNSTR_MAP.append(result)
        return return_value


class _LE_(CSummary):
    def run(self, var1, var2):
        return_value = self._incrementCC()
        result = var1.SLE(var2)
        CNSTR_MAP.append(result)
        return return_value


class _ULT_(CSummary):
    def run(self, var1, var2):
        return_value = self._incrementCC()
        result = var1.ULT(var2)
        CNSTR_MAP.append(result)
        return return_value


class _ULE_(CSummary):
    def run(self, var1, var2):
        return_value = self._incrementCC()
        result = var1.ULE(var2)
        CNSTR_MAP.append(result)
        return return_value


class _GT_(CSummary):
    def run(self, var1, var2):
        return_value = self._incrementCC()
        result = var1.SGT(var2)
        CNSTR_MAP.append(result)
        return return_value


class _GE_(CSummary):
    def run(self, var1, var2):
        return_value = self._incrementCC()
        result = var1.SGE(var2)
        CNSTR_MAP.append(result)
        return return_value


class _UGT_(CSummary):
    def run(self, var1, var2):
        return_value = self._incrementCC()
        result = var1.UGT(var2)
        CNSTR_MAP.append(result)
        return return_value


class _UGE_(CSummary):
    def run(self, var1, var2):
        return_value = self._incrementCC()
        result = var1.UGE(var2)
        CNSTR_MAP.append(result)
        return return_value


class _ITE_(CSummary):
    def run(self, restr_if_id, restr_then_id, restr_else_id):
        return_value = self._incrementCC()

        restr_if_id = self.state.solver.eval(restr_if_id)
        restr_then_id = self.state.solver.eval(restr_then_id)
        restr_else_id = self.state.solver.eval(restr_else_id)

        restr_if = CNSTR_MAP[restr_if_id]
        restr_then = CNSTR_MAP[restr_then_id]
        restr_else = CNSTR_MAP[restr_else_id]

        result = self.state.solver.If(restr_if, restr_then, restr_else)

        CNSTR_MAP.append(result)
        return return_value


class _ITE_VAR_(CSummary):
    def run(self, restr, sym1, sym2):

        restr = self.state.solver.eval(restr)
        restr_if = CNSTR_MAP[restr]

        result = self.state.solver.If(restr_if, sym1, sym2)
        result = result.sign_extend(self.state.arch.bits - result.size())

        try:
            return result
        except Exception as e:
            print(e)


summaries = [
    _NOT_,
    _OR_,
    _AND_,
    _EQ_,
    _NEQ_,
    _LT_,
    _LE_,
    _ULT_,
    _ULE_,
    _GT_,
    _GE_,
    _UGT_,
    _UGE_,
    _ITE_,
    _ITE_VAR_
]
