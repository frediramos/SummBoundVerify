from pycparser.c_ast import *


class API_Gen():
    def __init__(self):
        pass

    def save_current_state(self, name=None):

        if not name:
            return FuncCall(ID(f'save_current_state'), ExprList([]))

        lvalue = TypeDecl(name, [], None, IdentifierType(names=['state_t']))
        rvalue = FuncCall(ID(f'save_current_state'), ExprList([]))
        return Decl(name, [], [], [], [], lvalue, rvalue, None)

    def get_cnstr(self, name, ret_name, ret_type):

        if ret_type == 'void':
            args = [ID('NULL'), Constant('int', str(0))]

        else:
            args = [
                UnaryOp('&', ID(ret_name)),
                BinaryOp(op='*', left=FuncCall(ID('sizeof'),
                         ExprList([ID(ret_type)])), right=Constant('int', str(8)))
            ]

        lvalue = TypeDecl(name, [], None, IdentifierType(names=['cnstr_t']))
        rvalue = FuncCall(ID(f'get_cnstr'), ExprList(args))

        return Decl(name, [], [], [], [], lvalue, rvalue, None)

    def store_cnstr(self, cnstr_id, restr):
        return FuncCall(ID(f'store_cnstr'), ExprList([Constant('string', f'\"{cnstr_id}\"'), ID(restr)]))

    def halt_all(self, initial_state):
        return FuncCall(ID(f'halt_all'), ExprList([ID(initial_state)]))

    def check_implications(self, name, cnstr_id1, cnstr_id2):

        lvalue = TypeDecl(name, [], None, IdentifierType(names=['result_t']))
        rvalue = FuncCall(ID(f'check_implications'), ExprList(
            [Constant('string', f'\"{cnstr_id1}\"'), Constant('string', f'\"{cnstr_id2}\"')]))
        return Decl(name, [], [], [], [], lvalue, rvalue, None)

    def print_counterexamples(self, result):
        return FuncCall(ID(f'print_counterexamples'), ExprList([ID(result)]))

    def mem_addr(self, name, size):
        return FuncCall(ID(f'mem_addr'), ExprList([Constant('string', f'\"{name}\"'), ID(name), ID(size)]))
