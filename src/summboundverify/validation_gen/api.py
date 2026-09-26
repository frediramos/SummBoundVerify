from pycparser.c_ast import (
    ID,
    Decl,
    UnaryOp,
    PtrDecl,
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


def _is_void(ret_type) -> bool:
    """Whether `ret_type` (a type node, as parsed) is plain `void`."""
    return (
        isinstance(ret_type, TypeDecl)
        and getattr(ret_type.type, 'names', None) == ['void']
    )


def get_cnstr(name, ret_name: str, ret_type: Decl):
    call = ID(api_map().get_cnstr)
    cnstr_t = IdentifierType(names=['cnstr_t'])

    # A void function has no return value to lift: get_cnstr is told so by
    # a zero width, and never dereferences the NULL.
    if _is_void(ret_type):
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


def sbv_record(
    test_name: str,
    ret_name: str,
    ret_type,
    returns_void: bool,
    returns_pointer: bool = False,
):
    """
    Record this run's return value and tagged memory.
    The concrete counterpart of `get_cnstr` for fuzzing.
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
    call = ID(api_map().mem_addr)
    return FuncCall(
        call,
        ExprList([
            Constant('string', f'"{name}"'),
            ID(name),
            ID(size)
        ])
    )


def file_addr(name, path_var=None):
    call = ID(api_map().file_addr)
    path = ID(path_var) if path_var else ID(name)
    return FuncCall(
        call,
        ExprList([
            Constant('string', f'"{name}"'),
            path,
        ])
    )


def file_create(fname_var):
    call = ID(api_map().file_create)
    return FuncCall(call, ExprList([ID(fname_var)]))


def file_open(fd_name, fname_var, flags="w"):
    call = ID(api_map().file_open)
    int_t = IdentifierType(names=['int'])
    lvalue = TypeDecl(fd_name, [], None, int_t)
    rvalue = FuncCall(
        call,
        ExprList([ID(fname_var), Constant('string', f'"{flags}"')]),
    )
    return Decl(fd_name, [], [], [], [], lvalue, rvalue, None)


def file_write(fd_var, buf_var, count):
    call = ID(api_map().file_write)
    return FuncCall(
        call,
        ExprList([
            ID(fd_var),
            ID(buf_var),
            Constant('int', str(count)),
        ]),
    )


def file_set_offset(fd_var, offset=0):
    call = ID(api_map().file_set_offset)
    return FuncCall(
        call,
        ExprList([
            ID(fd_var),
            Constant('int', str(offset)),
        ]),
    )


def FILE_from_fd(name, fd_var):
    call = ID(api_map().FILE_from_fd)
    file_t = IdentifierType(names=['FILE'])
    ptr = PtrDecl([], TypeDecl(name, [], None, file_t))
    rvalue = FuncCall(call, ExprList([ID(fd_var)]))
    return Decl(name, [], [], [], [], ptr, rvalue, None)
