from pycparser.c_ast import *

from ..api_gen import API_Gen
from ..utils import returnValue

from .arg_gen import Symbolic_Args


class TestGen:
    def __init__(self, args, ret, cncrt_name, summ_name, memory, max_args):
        self.args = args
        self.ret = ret
        self.memory = memory
        self.cncrt_name = cncrt_name
        self.summ_name = summ_name
        self.max_args = max_args

    def call_function(self, fname, call_args, ret_name, ret_type):
        lvalue = TypeDecl(ret_name, [], None, IdentifierType(names=[ret_type]))
        rvalue = FuncCall(ID(fname), ExprList(
            [a for a in map(lambda x: ID(x), call_args)]))
        if ret_type == 'void':
            return rvalue
        return Decl(ret_name, [], [], [], [], lvalue, rvalue, None)

    def tag_memory(self, gen, ptr_names, size_macro):
        code = []
        if isinstance(size_macro, list):
            for ptr, size in zip(ptr_names, size_macro):
                code.append(gen.mem_addr(ptr, size))
        else:
            for ptr in ptr_names:
                code.append(gen.mem_addr(ptr, size_macro))
        return code

    def createTest(self, name, size_macro,
                   null_bytes, max_macro,
                   default, concrete, id):

        # Helper objects
        sym_args_gen = Symbolic_Args(
            self.args, size_macro, null_bytes, max_macro, self.max_args)
        api_gen = API_Gen()

        # Create symbolic args
        args_code = sym_args_gen.create_symbolic_args(default, concrete)

        # Get ordered arg names
        args_names = sym_args_gen.get_all_args()

        # Body contains the test code
        body = [
            *args_code,
            api_gen.save_current_state('initial_state'),
        ]

        if self.memory:
            ptr_names = sym_args_gen.get_ptr_args()
            body += self.tag_memory(api_gen, ptr_names, size_macro)

        body += [
            self.call_function(self.cncrt_name, args_names, 'ret1', self.ret),
            api_gen.get_cnstr('cnstr1', 'ret1', self.ret),
            api_gen.store_cnstr(f'cnctr_test{id}', 'cnstr1'),

            api_gen.halt_all('initial_state'),

            self.call_function(self.summ_name, args_names, 'ret2', self.ret),
            api_gen.get_cnstr('cnstr2', 'ret2', self.ret),
            api_gen.store_cnstr(f'summ_test{id}', 'cnstr2'),

            api_gen.halt_all('NULL'),

            api_gen.check_implications(
                'result', f'cnctr_test{id}', f'summ_test{id}'),
            api_gen.print_counterexamples('result'),

            # Return
            returnValue(None)
        ]

        # Create function ast
        block = Compound(body)

        typedecl = TypeDecl(name, [], None, IdentifierType(names=['void']))
        funcdecl = FuncDecl(None, typedecl)
        decl = Decl(name, [], [], [], [], funcdecl, None, None)

        return FuncDef(decl, None, block)
