from pycparser.c_ast import (
    ID,
    Decl,
    UnaryOp,
    FuncCall,
    ExprList,
    TypeDecl,
    Constant,
    BinaryOp,
    IdentifierType,
)

from summboundverify.api import api_map


def save_current_state(name=None):
    call = ID(api_map().save_current_state)
    state_t = IdentifierType(names=['state_t'])

    if not name:
        return FuncCall(call, ExprList([]))

    lvalue = TypeDecl(name, [], None, state_t)
    rvalue = FuncCall(call, ExprList([]))
    decl = Decl(name, [], [], [], [], lvalue, rvalue, None)
    return decl


def get_cnstr(name, ret_name: str, ret_type: Decl):
    call = ID(api_map().get_cnstr)
    cnstr_t = IdentifierType(names=['cnstr_t'])

    if ret_type == 'void':
        args = [ID('NULL'), Constant('int', str(0))]

    else:
        args = [
            UnaryOp('&', ID(ret_name)),

            BinaryOp(  # Multiplication
                op='*',
                left=FuncCall(
                    ID('sizeof'),
                    ExprList([ret_type])
                ),
                right=Constant('int', str(8))
            )
        ]

    lvalue = TypeDecl(name, [], None, cnstr_t)
    rvalue = FuncCall(call, ExprList(args))
    decl = Decl(name, [], [], [], [], lvalue, rvalue, None)
    return decl


def store_cnstr(cnstr_id, restr):
    call = ID(api_map().store_cnstr)
    return FuncCall(call, ExprList([Constant('string', f'"{cnstr_id}"'), ID(restr)]))


def halt_all(initial_state):
    call = ID(api_map().halt_all)
    return FuncCall(call, ExprList([ID(initial_state)]))


def check_implications(name, cnstr_id1, cnstr_id2):
    call = ID(api_map().check_implications)
    result_t = IdentifierType(names=['result_t'])

    lvalue = TypeDecl(name, [], None, result_t)

    rvalue = FuncCall(
        call,
        ExprList([
            Constant('string', f'"{cnstr_id1}"'),
            Constant('string', f'"{cnstr_id2}"')
        ])
    )
    decl = Decl(name, [], [], [], [], lvalue, rvalue, None)
    return decl


def print_counterexamples(result):
    call = ID(api_map().print_counterexamples)
    return FuncCall(call, ExprList([ID(result)]))


def mem_addr(name, size):
    call = ID(api_map().mem_addr)
    return FuncCall(
        call,
        ExprList([
            Constant('string', f'"{name}"'),
            ID(name),
            ID(size)
        ])
    )
