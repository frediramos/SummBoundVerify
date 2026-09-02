import os
import json
import claripy
import logging

from pathlib import Path

from angr import SimulationManager

from claripy.ast.bv import BV as BitVector
from claripy.backends.backend_z3 import BackendZ3

from z3 import (
    Solver,
    Exists,
    ExprRef,
    Or,
    Not,
    simplify,
    sat
)

from summboundverify.exceptions import InvalidSymbolicVariableSizeError


from ...summary import CSummary
from ...context import ValidationCTX

from ..utils import get_name

from .models import to_signed_int
from .output import ValidationOutput
from .result import Under, Over, Exact, Unkown


logger = logging.getLogger(__name__)


class save_current_state(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def get_input_vars(self):
        input_vars = []
        for var in self.ctx.SYM_VARS.keys():
            input_vars += self.ctx.SYM_VARS[var]
        return input_vars

    def run(self):

        self.ctx.INPUT_VARS = self.get_input_vars()

        new_state = self.state.copy()

        self.ctx.SYM_STATES[self.ctx.STATE_ID] = new_state
        ret = self.ctx.STATE_ID
        self.ctx.STATE_ID += 1

        self.ret(ret)


class get_cnstr(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def value_fromBV(self, bv):
        '''
        Get the concrete value from a single valued bitvec
        '''
        bytes_ = self.state.solver.eval(bv, cast_to=bytes)
        value = int.from_bytes(bytes_, byteorder='big', signed=True)
        return value

    def _memory_cnstrs(self, addr, nbytes, prefix):
        cnstrs = []
        sym_vars = []
        for i in range(nbytes):

            name = f'{prefix}_{i}'
            sym_var = self.state.solver.BVS(name, 8, explicit_name=True)

            sym_vars.append(sym_var)
            cnstrs.append(sym_var == self.state.memory.load(addr + i, 1))

        return (sym_vars, cnstrs)

    def get_memory(self):
        cnstrs = []

        for triple in self.ctx.MEMORY_TRIPLES:
            name, addr, nbytes = triple
            name = "mem_{}".format(name)

            vars, cnstr = self._memory_cnstrs(addr, nbytes, name)

            self.ctx.MEMORY_SYM_VARS[name] = vars
            cnstrs += cnstr

        return cnstrs

    def run(self, var_addr, length):

        backend_z3 = BackendZ3()

        # Increment CNSTR_COUNTER
        return_value = self.ctx.CNSTR_COUNTER
        self.ctx.CNSTR_COUNTER += 1

        length = self.state.solver.eval(length)
        if length % 8 != 0:
            raise InvalidSymbolicVariableSizeError(length)

        # Lift memory contents for functions with side-effects
        mem_cnstrs = self.get_memory()
        mem_cnstrs = claripy.And(*mem_cnstrs)

        c = self.state.solver.constraints

        # Ignore Ret for void functions
        if length != 0:

            var = self.state.memory.load(
                var_addr,
                int(length/8),
                endness=self.state.arch.memory_endness
            )

            # #Symbolic or Single Valued
            # if not self.state.solver.symbolic(var):
            # 	var = self.value_fromBV(var)
            # 	var = self.state.solver.BVV(var, self.state.arch.bits)

            ret = self.state.solver.BVS("Ret", length, explicit_name=True)
            self.ctx.RET = ret
            c.append(ret == var)

        c.append(mem_cnstrs)
        c = claripy.And(*c)

        converted = backend_z3.convert(c)
        self.ctx.CNSTR_MAP.append(converted)

        self.ret(return_value)


class store_cnstr(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, name_addr, cnstr_id):

        cnstr_id = self.state.solver.eval(cnstr_id)
        assert isinstance(cnstr_id, int)
        assert (cnstr_id >= 0)

        cnstr = self.ctx.CNSTR_MAP[cnstr_id]

        name = get_name(self.state, name_addr)

        # Store cnstrcition in dict
        if name not in self.ctx.STORED_CNSTR.keys():
            self.ctx.STORED_CNSTR[name] = []

        self.ctx.STORED_CNSTR[name].append(cnstr)

        self.ret()


class halt_all(CSummary):

    def __init__(self, ctx: ValidationCTX, sm):
        self.sm = sm
        super().__init__(ctx)

    def get_ret_addr(self):
        '''
        Get return address of the current sym state
        '''

        ret = self.cc.teardown_callsite(  # type: ignore
            self.state,
            None,
            prototype=self.prototype
        )

        return ret

    def activate_state(self, state, addr):
        '''
        'Activate' a symbolic state
        @state: symbolic state object
        @addr: Instruction pointer to start from
        '''

        self.successors.add_successor(  # type: ignore
            state,
            addr,
            claripy.true(),
            'Ijk_Ret'
        )

    def all_done(self):
        active_states = {str(s) for s in self.sm.active}
        if len(active_states) == 1:
            return True
        return False

    def run(self, state_bv: BitVector):
        state_id = self.state.solver.eval(state_bv)
        state_id = to_signed_int(state_id)

        # Receives NULL
        # End of symbolic execution
        if state_id == 0:
            self.ctx.SUMM_PATHS += 1
            if self.all_done() and not self.ctx.REACHED_NULL:
                self.ctx.REACHED_NULL = True
                self.ret()
            else:
                self.exit(0)  # Stop the state

        # Receives a normal state
        # End of concrete execution
        else:
            self.ctx.CNCR_PATHS += 1
            if self.all_done() and not self.ctx.REACHED_HALT:
                self.ctx.REACHED_HALT = True
                state = self.ctx.SYM_STATES[state_id]
                ret_addr = self.get_ret_addr()
                self.activate_state(state, ret_addr)

            self.exit(0)  # Stop the state


class mem_addr(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def run(self, name_addr, mem_addr, size):

        size = self.state.solver.eval(size)
        name = get_name(self.state, name_addr)

        triple = (name, mem_addr, size)
        self.ctx.MEMORY_TRIPLES.append(triple)

        self.ret()


class check_implications(CSummary):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def summary_generated(self) -> list[BitVector]:
        '''
        Returns a list of sym_vars generated
        by the summary being tested
        '''

        new_vars = list(
            set(self.state.solver.all_variables) - set(self.ctx.INPUT_VARS)
        )

        # Convert to Z3 and remove 'ret' sym var
        backend_z3 = BackendZ3()
        converted = [backend_z3.convert(var) for var in new_vars]

        def filter_vars(var):
            unwanted = ['Ret', 'reg', 'mem']
            for symbol in unwanted:
                if symbol in str(var):
                    return False
            return True

        ret = filter(filter_vars, converted)
        return list(ret)

    def check(self, summ: ExprRef, cncrt: ExprRef):

        # Create 2 solvers to verify both implications
        # A ∧ ~B; B ∧ ~A
        solver1 = Solver()
        solver2 = Solver()

        new_vars = self.summary_generated()
        if len(new_vars) > 0:
            summ = Exists(new_vars, summ)

        # Under-approximation
        solver1.add(summ)
        solver1.add(Not(cncrt))

        # Over-approximation
        solver2.add(cncrt)
        solver2.add(Not(summ))

        # Verify satisfiability
        solver1_sat = solver1.check() == sat
        solver2_sat = solver2.check() == sat

        if not solver1_sat and not solver2_sat:
            ret = Exact(summ, cncrt, new_vars)

        elif not solver1_sat:
            ret = Under(summ, cncrt, new_vars)

        elif not solver2_sat:
            ret = Over(summ, cncrt, new_vars)

        else:
            ret = Unkown(summ, cncrt, new_vars)
        return ret

    def run(self, key1, key2):

        key1 = get_name(self.state, key1)
        key2 = get_name(self.state, key2)

        if 'summ' in key1.lower():
            summ = key1
            cncrt = key2
        elif 'summ' in key2.lower():
            summ = key2
            cncrt = key1
        else:
            summ = key1
            cncrt = key2

        summ = simplify(Or(self.ctx.STORED_CNSTR[summ]))
        cncrt = simplify(Or(self.ctx.STORED_CNSTR[cncrt]))

        result = self.check(summ, cncrt)

        # Increment RESULTS_COUNTER
        return_value = self.ctx.RESULTS_COUNTER
        self.ctx.RESULTS_COUNTER += 1
        self.ctx.RESULTS.append(result)

        self.ret(return_value)


class print_counterexamples(CSummary):

    def __init__(
        self,
        ctx: ValidationCTX,
        sm: SimulationManager,
        binary_name: str,
        results_dir: str | Path,
        convert_ascii=False
    ):

        super().__init__(ctx)

        self.sm = sm
        self.binary_name = binary_name
        self.results_dir = Path(results_dir)
        self.convert_ascii = convert_ascii

    def reset(self):
        '''(small) HACK: reset context in between test executions'''
        self.ctx.archive()
        self.ctx.reset()

    def save_json(self, json_result: dict):
        self.ctx.TEST_COUNT += 1

        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)

        testid = f"{self.binary_name}_{self.ctx.TEST_COUNT}"
        testname = f"{self.binary_name}_result.json"
        out = self.results_dir / testname

        self.ctx.JSON_LOG[testid] = json_result
        json_object = json.dumps(self.ctx.JSON_LOG, indent=2)

        with open(out, 'w') as f:
            f.write(json_object)

    def run(self, result_bv: BitVector):
        result_id = self.state.solver.eval(result_bv)
        assert isinstance(result_id, int)

        result = self.ctx.RESULTS[result_id]
        ignore = [str(i) for i in result.ignore]

        output = ValidationOutput(result)
        text_result = output.text_log()
        json_result = output.json_result(self.ctx, ignore, self.convert_ascii)

        self.save_json(json_result)

        logger.info('\n' + text_result)

        self.reset()
        self.ret()
