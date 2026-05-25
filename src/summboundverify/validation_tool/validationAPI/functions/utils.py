from collections import OrderedDict

from z3 import BitVecNumRef, Solver, Not, sat
from claripy.backends.backend_z3 import BackendZ3


'''Aux Functions'''


def get_name(state, addr):
    """
    Get a null terminated string from a Simprocedure
    @addr: Address of the first byte (SymActionObject type)
    """

    name = ''
    i = 0
    while True:
        char_code = state.solver.\
            eval(state.memory.load(addr + i, 1, endness='Iend_LE'))

        if char_code == 0:
            break

        char = chr(char_code)
        name += char
        i += 1
    return name


# Signedness-----------------------------------------
def _bit_is_set(num, bit):
    bit = int('1' + '0'*bit, 2)
    return num & bit != 0


def to_signed_char(number):
    if _bit_is_set(number, 8-1):
        number = -(-number & 0xFF)
    return number


def to_signed_int(number):
    if _bit_is_set(number, 32-1):
        number = -(-number & 0xFFFFFFFF)
    return number


def to_signed_long(number):
    if _bit_is_set(number, 64-1):
        number = -(-number & 0xFFFFFFFFFFFFFFFF)
    return number


# Process model-----------------------------------------
class Pretty_Model():

    def __init__(self, input_vars, mem_vars, ret, ignore, convert_chars):
        self.input_vars = input_vars
        self.mem_vars = mem_vars
        self.ret = ret
        self.ignore = ignore
        self.convert_chars = convert_chars

    # Return a numeric value from a sym_var in a z3 model

    def evaluate_sym_var(self, var, model):

        value = model.evaluate(var)
        size = var.size()

        if isinstance(value, BitVecNumRef):
            num_value = value.as_long()

            if size == 32:
                num_value = to_signed_int(num_value)
            elif size == 64:
                num_value = to_signed_long(num_value)

            return num_value

        else:
            return 'Not in model'

    # Pretify input variables
    def _prettify_input(self, model, json_obj):

        for var in self.input_vars.keys():

            if var in self.ignore:
                continue

            json_obj[var] = OrderedDict()

            for v in self.input_vars[var]:

                backend_z3 = BackendZ3()
                v = backend_z3.convert(v)
                size = v.size()

                value = self.evaluate_sym_var(v, model)

                if isinstance(value, int) and size == 8:
                    if self.convert_chars and size == 8 and chr(value).isprintable():
                        value = chr(value)
                    else:
                        value = to_signed_char(value)

                json_obj[var][str(v)] = value

            if len(json_obj[var].keys()) == 1:
                json_obj[var] = list(json_obj[var].values())[0]

        return json_obj

    # Pretify return variable

    def _prettify_ret(self, model, json_obj):
        backend_z3 = BackendZ3()
        ret = backend_z3.convert(self.ret)
        size = ret.size()

        ret_val = self.evaluate_sym_var(ret, model)

        if self.convert_chars and \
                size == 8 and \
                chr(ret_val).isprintable():
            ret_val = chr(ret_val)

        json_obj['ret'] = ret_val
        return json_obj

    # Pretify memory variables
    def _prettify_mem(self, model, json_obj):
        if self.mem_vars.keys():
            json_obj['memory'] = OrderedDict()

            for var in self.mem_vars.keys():
                json_obj['memory'][var] = OrderedDict()

                for v in self.mem_vars[var]:
                    backend_z3 = BackendZ3()
                    v = backend_z3.convert(v)

                    value = self.evaluate_sym_var(v, model)
                    json_obj['memory'][var][str(v)] = value

        return json_obj

    # Pretify model

    def prettify(self, model):
        json_obj = self._prettify_input(model, OrderedDict())
        json_obj = self._prettify_ret(model, json_obj)
        json_obj = self._prettify_mem(model, json_obj)

        return json_obj


# Aux functions-----------------------------------------
def is_leaf_memory(mem):
    return not mem.has_children


def get_all_restrs(mem):
    '''
    Get all restrictions of a memory
    including parent memories
    (build an execution path) 
    '''

    final_restrs = []
    while mem is not None:
        final_restrs += mem.next_restr
        mem = mem.parent_mem

    return final_restrs


def remove_duplicates(l):
    '''
    Remove duplicates in a list
    '''
    return list(set(l))


# Implication Results------------------------------------------------------
class Result():
    def __init__(self, result, summ, cncrt, vars):
        self.internal_result = result
        self.summ = summ
        self.cncrt = cncrt
        self.vars = vars

    def __str__(self):
        return self.internal_result

    def __eq__(self, other):
        return self.internal_result == other


class Equivalent(Result):
    def __init__(self, summ, cncrt, vars):
        super().__init__('equivalent', summ, cncrt, vars)

    def implication(self):

        impl = ('Summary ^ ~Cncrt_Function: unsat\n'
                'Cncrt_Function ^ ~Summary: unsat\n'
                'Summary -> Cncrt_Function ^ Cncrt_Function -> Summary')

        return impl

    def result(self):
        res = 'Summary and Concrete function are equivalent'
        return res

    def simple_result(self):
        return 'Exact'

    def models(self):
        return None


class Under(Result):
    def __init__(self, summ, cncrt, vars):
        super().__init__('under', summ, cncrt, vars)

    def implication(self):
        impl = ('Summary ^ ~Cncrt_Function: unsat\n'
                'Cncrt_Function ^ ~Summary: sat\n'
                'Summary -> Cncrt_Function')

        return impl

    def result(self):
        res = 'Summary under-approximates the concrete function'
        return res

    def simple_result(self):
        return 'Under-approximation'

    # Create solver to generate models
    # Missing path
    def create_solver(self):
        solver = Solver()

        solver.add(Not(self.summ))
        solver.add(self.cncrt)
        return solver

    def models(self):
        solver = self.create_solver()
        assert solver.check() == sat
        model = solver.model()
        return model


class Over(Result):
    def __init__(self, summ, cncrt, vars):
        super().__init__('over', summ, cncrt, vars)

    def implication(self):

        impl = ('Summary ^ ~Cncrt_Function: sat\n'
                'Cncrt_Function ^ ~Summary: unsat\n'
                'Cncrt_Function -> Summary')

        return impl

    def result(self):
        res = 'Summary over-approximates the concrete function'
        return res

    def simple_result(self):
        return 'Over-approximation'

    # Create solver to generate models
    # Wrong path

    def create_solver(self):
        solver = Solver()

        solver.add(self.summ)
        solver.add(Not(self.cncrt))
        return solver

    def models(self):
        solver = self.create_solver()
        assert solver.check() == sat
        model = solver.model()
        return model


class Unkown(Result):
    def __init__(self, summ, cncrt, vars):
        super().__init__('unknown', summ, cncrt, vars)

    def implication(self):

        impl = ('Summary ^ ~Cncrt_Function: sat\n'
                'Cncrt_Function ^ ~Summary: sat')

        return impl

    def result(self):
        res = 'Summary is not an over/under-approximation of the concrete function'
        return res

    def simple_result(self):
        return 'N/A (Not under/over-approximation)'

    # Create solver to generate models
    def create_solvers(self):

        # Missing path
        solver1 = Solver()

        solver1.add(Not(self.summ))
        solver1.add(self.cncrt)

        # Wrong path
        solver2 = Solver()
        solver2.add(self.summ)
        solver2.add(Not(self.cncrt))
        return (solver1, solver2)

    def models(self):
        solver1, solver2 = self.create_solvers()
        assert solver1.check() == sat
        model1 = solver1.model()

        assert solver2.check() == sat
        model2 = solver2.model()

        return (model1, model2)
