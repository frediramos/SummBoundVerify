from .constraints import init as init_constraints
from .solver import init as init_solver
from .validation import init as init_validation


def init_api():
    init_constraints()
    init_solver()
    init_validation()
