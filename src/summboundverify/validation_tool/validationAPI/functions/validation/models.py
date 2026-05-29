import logging

from collections import OrderedDict

from claripy.backends.backend_z3 import BackendZ3

from z3 import BitVecNumRef, ModelRef

from .utils import (
    to_signed_int,
    to_signed_char,
    to_signed_long
)

logger = logging.getLogger(__name__)


class PrettyModel():

    def __init__(self, input_vars, mem_vars, ret, ignore, convert_chars):
        self.input_vars = input_vars
        self.mem_vars = mem_vars
        self.ret = ret
        self.ignore = ignore
        self.convert_chars = convert_chars

    # Return a numeric value from a sym_var in a z3 model
    def evaluate_sym_var(self, var, model: ModelRef):

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
                    if self.convert_chars:
                        if (converted := chr(value)).isprintable():
                            value = converted
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

        retval = self.evaluate_sym_var(ret, model)

        if (
            isinstance(retval, int) and
            self.convert_chars and
            size == 8
        ):
            try:
                if (char := chr(retval)).isprintable():
                    retval = char
            except ValueError:
                msg = f"Could not convert to char: {retval}"
                logger.debug(msg)

        json_obj['ret'] = retval
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
