import json
import os
from angr import SimProcedure

from claripy.backends.backend_z3 import BackendZ3
from z3 import simplify, Or, Not, Solver, sat, Exists

from collections import OrderedDict

from ..utils import get_states

from .solver import SYM_VARS
from .utils import *


# Reached halt_all
REACHED_NULL = False
REACHED_HALT = False

# Restrictions
# ------------------------------------------------------
RESTR_MAP = []
RESTR_COUNTER = 0

# Input Variables
# ------------------------------------------------------
INPUT_VARS = []

# Return variable
# ------------------------------------------------------
RET = None

# Symbolic states
# ------------------------------------------------------
SYM_STATES = {}
STATE_ID = 1

# Stored Restrictions
STORED_RESTR = {}
# ------------------------------------------------------

# Memory
# ------------------------------------------------------
# Segments of memory tagged to be evaluated
# List of tuples: (name, start_addr, nbytes)
MEMORY_TRIPLES = []
MEMORY_SYM_VARS = OrderedDict()


# Validation results
# ------------------------------------------------------
# Results of the implications
# These are supplied to print_counterexamples
RESULTS = []
RESULTS_COUNTER = 0

# Logging
# ------------------------------------------------------
TEST_COUNT = 0
JSON_LOG = {}

# Path stats
# ------------------------------------------------------
SUMM_PATHS = 0
CNCR_PATHS = 0


'''Validation Primitives'''


class save_current_state(SimProcedure):

    def get_input_vars(self):
        input_vars = []
        for var in SYM_VARS.keys():
            input_vars += SYM_VARS[var]
        return input_vars

    def run(self):
        global STATE_ID
        global INPUT_VARS

        INPUT_VARS = self.get_input_vars()

        new_state = self.state.copy()

        SYM_STATES[STATE_ID] = new_state
        ret = STATE_ID
        STATE_ID += 1

        self.ret(ret)


class get_cnstr(SimProcedure):

    def value_fromBV(self, bv):
        '''
        Get the concrete value from a single valued bitvec
        '''
        bytes_ = self.state.solver.eval(bv, cast_to=bytes)
        value = int.from_bytes(bytes_, byteorder='big', signed=True)
        return value

    def memory_restrictions_aux(self, addr, nbytes, prefix):
        restrs = []
        sym_vars = []
        for i in range(nbytes):

            name = f'{prefix}_{i}'
            sym_var = self.state.solver.BVS(name, 8, explicit_name=True)

            sym_vars.append(sym_var)
            restrs.append(sym_var == self.state.memory.load(addr + i, 1))

        return (sym_vars, restrs)

    def get_memory(self):
        restrs = []

        for triple in MEMORY_TRIPLES:
            name, addr, nbytes = triple
            memory_name = "mem_{}".format(name)

            vars, restr = self.memory_restrictions_aux(
                addr, nbytes, memory_name)

            MEMORY_SYM_VARS[name] = vars
            restrs += restr

        return restrs

    def run(self, var_addr, length):
        global RESTR_COUNTER
        global RET

        backend_z3 = BackendZ3()

        # Increment RESTR_COUNTER
        return_value = RESTR_COUNTER
        RESTR_COUNTER += 1

        length = self.state.solver.eval(length)
        assert length % 8 == 0, \
            "[!] Size in bits must be divisible by 8!"

        # Lift memory contents for functions with side-effects
        mem_restrs = self.get_memory()
        mem_restrs = self.state.solver.And(*mem_restrs)

        c = self.state.solver.constraints

        # Ignore Ret for void functions
        if length != 0:

            var = self.state.memory.load(var_addr,  int(
                length/8), endness=self.state.arch.memory_endness)

            # #Symbolic or Single Valued
            # if not self.state.solver.symbolic(var):
            # 	var = self.value_fromBV(var)
            # 	var = self.state.solver.BVV(var, self.state.arch.bits)

            ret = self.state.solver.BVS("Ret", length, explicit_name=True)
            RET = ret
            c.append(ret == var)

        c.append(mem_restrs)
        c = self.state.solver.And(*c)

        converted = backend_z3.convert(c)
        RESTR_MAP.append(converted)

        self.ret(return_value)


class store_cnstr(SimProcedure):

    def run(self, name_addr, restr_id):

        restr_id = self.state.solver.eval(restr_id)
        assert (restr_id >= 0)

        restr = RESTR_MAP[restr_id]

        name = get_name(self.state, name_addr)

        # Store Restrcition in dict
        if name not in STORED_RESTR.keys():
            STORED_RESTR[name] = []

        STORED_RESTR[name].append(restr)

        self.ret()


class halt_all(SimProcedure):

    def __init__(self, sm):
        self.sm = sm
        super().__init__()

    def get_ret_addr(self):
        '''
        Get return address of the current sym state
        '''

        ret = self.cc.teardown_callsite(
            self.state, None, prototype=self.prototype)

        return ret

    def activate_state(self, state, addr):
        '''
        'Activate' a symbolic state
        @state: symbolic state object
        @addr: Instruction pointer to start from
        '''

        self.successors.add_successor(
            state, addr, self.state.solver.true, 'Ijk_Ret')

    def all_done(self):

        n_active = len(self.sm.active)
        active_states = [str(s) for s in self.sm.active]

        # HACK: Sometimes when calling 'self.exit(0)' the state is stopped but it is
        # still kept in the active stash. To address this, we check if the number
        # of active states is equal to 1 _OR_ all active states have the same instr pointer
        # i.e., the 'halt_all' addr

        if n_active == 1 or len(list(dict.fromkeys(active_states))) == 1:
            return True

        return False

    def run(self, state_id):
        global REACHED_HALT
        global REACHED_NULL
        global CNCR_PATHS

        state_id = self.state.solver.eval(state_id)
        state_id = to_signed_int(state_id)

        # Receives NULL
        if state_id == 0:
            if self.all_done() and not REACHED_NULL:
                REACHED_NULL = True
                self.ret()
            else:
                self.exit(0)  # Simply exit otherwise

        # Receives a normal state
        else:
            if self.all_done() and not REACHED_HALT:
                REACHED_HALT = True
                state = SYM_STATES[state_id]
                ret_addr = self.get_ret_addr()
                self.activate_state(state, ret_addr)

            self.exit(0)

        CNCR_PATHS = len(get_states(self.sm))


class mem_addr(SimProcedure):

    def run(self, name_addr, mem_addr, size):

        size = self.state.solver.eval(size)
        name = get_name(self.state, name_addr)

        triple = (name, mem_addr, size)
        MEMORY_TRIPLES.append(triple)

        self.ret()


class check_implications(SimProcedure):

    def summary_generated(self):
        '''
        Returns a list of sym_vars generated
        by the summary being tested
        '''

        new_vars = list(set(self.state.solver.all_variables) - set(INPUT_VARS))

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

    def check(self, summ, cncrt):

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
            ret = Equivalent(summ, cncrt, new_vars)

        elif not solver1_sat:
            ret = Under(summ, cncrt, new_vars)

        elif not solver2_sat:
            ret = Over(summ, cncrt, new_vars)

        else:
            ret = Unkown(summ, cncrt, new_vars)
        return ret

    def run(self, key1, key2):
        global RESULTS_COUNTER

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

        summ = simplify(Or(STORED_RESTR[summ]))
        cncrt = simplify(Or(STORED_RESTR[cncrt]))

        result = self.check(summ, cncrt)

        # Increment RESULTS_COUNTER
        return_value = RESULTS_COUNTER
        RESULTS_COUNTER += 1
        RESULTS.append(result)

        self.ret(return_value)


class print_counterexamples(SimProcedure):

    def __init__(self, sm,
                 binary_name: str,
                 results_dir: str,
                 convert_ascii=False):

        self.sm = sm
        self.binary_name = binary_name
        self.results_dir = results_dir
        self.convert_ascii = convert_ascii

        super().__init__()

    def reset(self):
        '''HACK: clear memory pairs, sym vars, and input_vars
        in between test executions
        '''
        global REACHED_NULL
        global REACHED_HALT

        MEMORY_TRIPLES.clear()
        SYM_VARS.clear()
        INPUT_VARS.clear()
        REACHED_NULL = False
        REACHED_HALT = True

    def log_json(self, result, models, path):
        global TEST_COUNT
        global JSON_LOG

        TEST_COUNT += 1

        file = open(path, 'w')
        log = {
            'result': f'{result.simple_result()}',
        }

        ignore = [str(i) for i in result.vars]
        pm = Pretty_Model(SYM_VARS, MEMORY_SYM_VARS, RET,
                          ignore, convert_chars=self.convert_ascii)

        if result == 'unknown':
            missing, wrong = models

            p_missing = pm.prettify(missing)
            p_wrong = pm.prettify(wrong)

            log['counterexamples'] = {
                'Over-approximation': p_missing,
                'Under-approximation': p_wrong
            }

        elif result == 'under':
            model = models
            p_model = pm.prettify(model)
            log['counterexamples'] = {
                'Over-approximation': p_model
            }

        elif result == 'over':
            model = models
            p_model = pm.prettify(model)

            log['counterexamples'] = {
                'Under-approximation': p_model
            }

        else:
            log['counterexamples'] = {}

        testid = f'{self.binary_name}_{TEST_COUNT}'
        JSON_LOG[testid] = log
        json_object = json.dumps(JSON_LOG, indent=2)
        file.write(json_object)

    def run(self, result_id):
        result_id = self.state.solver.eval(result_id)

        result = RESULTS[result_id]
        models = result.models()

        log = (f'===================== Result ===================== \n\n'
               f'==> Concrete Constraints: \n\t{result.cncrt}\n\n'
               f'==> Summary Constraints: \n\t{result.summ}\n\n'
               f'==> Existencial Variables: \n\t{result.vars}\n\n'
               f'==> Result: {result.result()}\n\n'
               f'==> Implication: \n{result.implication()}\n\n')

        if result != 'equivalent':
            log += f'==> Counterexamples: \n'
            if result == 'under':
                log += f'Missing path example: \n{models}\n\n\n'
            elif result == 'over':
                log += f'Wrong path example: \n{models}\n\n\n'
            else:
                missing, wrong = models
                log += f'Missing path example: \n{missing}\n\n'
                log += f'Wrong path example: \n{wrong}\n\n'

        print(log.rstrip())

        # Create outputs folder if it does not exist yet
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)

        json_log_path = f'{self.results_dir}/{self.binary_name}_result.json'
        self.log_json(result, models, json_log_path)

        self.reset()
        self.ret()

        global SUMM_PATHS
        SUMM_PATHS = len(get_states(self.sm))


summaries = [
    save_current_state,
    get_cnstr,
    store_cnstr,
    mem_addr,
    check_implications,

    # These primitives require input arguments
    # (Must be instantiated manually in the engine)
    # halt_all,
    # print_counterexamples,
]
