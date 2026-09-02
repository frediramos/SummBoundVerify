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


def save_current_state(name=None):
    if not name:
        return FuncCall(ID(f'save_current_state'), ExprList([]))

    lvalue = TypeDecl(name, [], None, IdentifierType(names=['state_t']))
    rvalue = FuncCall(ID(f'save_current_state'), ExprList([]))
    decl = Decl(name, [], [], [], [], lvalue, rvalue, None)
    return decl


def get_cnstr(name, ret_name: str, ret_type: Decl):
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
                right=Constant('int', str(8)))
        ]

    lvalue = TypeDecl(name, [], None, IdentifierType(names=['cnstr_t']))
    rvalue = FuncCall(ID(f'get_cnstr'), ExprList(args))
    decl = Decl(name, [], [], [], [], lvalue, rvalue, None)
    return decl


def store_cnstr(cnstr_id, restr):
    return FuncCall(
        ID(f'store_cnstr'),
        ExprList([Constant('string', f'"{cnstr_id}"'), ID(restr)])
    )


def halt_all(initial_state):
    return FuncCall(
        ID(f'halt_all'),
        ExprList([ID(initial_state)])
    )


def check_implications(name, cnstr_id1, cnstr_id2):
    lvalue = TypeDecl(name, [], None, IdentifierType(names=['result_t']))

    rvalue = FuncCall(
        ID(f'check_implications'),
        ExprList(
            [
                Constant('string', f'"{cnstr_id1}"'),
                Constant('string', f'"{cnstr_id2}"')]
        )
    )
    decl = Decl(name, [], [], [], [], lvalue, rvalue, None)
    return decl


def print_counterexamples(result):
    return FuncCall(
        ID(f'print_counterexamples'),
        ExprList([ID(result)])
    )


def sbv_record(
    test_name: str,
    ret_name: str,
    ret_type,
    returns_void: bool,
    returns_pointer: bool = False,
):
    """Record this run's return value and tagged memory.

    The sampling counterpart of get_cnstr: same moment, same operands, but it
    writes down what the concrete function actually produced instead of a
    formula denoting what it could produce.

    `returns_pointer` travels with the value because the checker cannot tell
    an address from an integer by looking at the bytes, and the two are not
    checked the same way.
    """
    if returns_void:
        args = [Constant('int', str(0)), Constant('int', str(0))]

    else:
        args = [
            UnaryOp('&', ID(ret_name)),
            BinaryOp(
                op='*',
                left=FuncCall(ID('sizeof'), ExprList([ret_type])),
                right=Constant('int', str(8)),
            ),
        ]

    return FuncCall(
        ID('sbv_record'),
        ExprList([
            Constant('string', f'"{test_name}"'),
            *args,
            Constant('int', str(int(returns_pointer))),
        ])
    )


def mem_addr(name, size):
    return FuncCall(
        ID(f'mem_addr'),
        ExprList([
            Constant('string', f'"{name}"'),
            ID(name),
            ID(size)
        ])
    )
