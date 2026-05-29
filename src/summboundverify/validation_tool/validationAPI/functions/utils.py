from angr import SimState
from claripy.ast.bv import BV as BitVector


def get_name(state: SimState, addr):
    """
    Get a null terminated string from a Simprocedure
    @addr: Address of the first byte (SymActionObject type)
    """

    name = ''
    i = 0
    while True:
        byte: BitVector = state.memory.load(
            addr + i, 1,
            endness='Iend_LE'
        )
        code = state.solver.eval(byte)

        if code == 0:
            break

        char = chr(code)
        name += char
        i += 1

    return name
