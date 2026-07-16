from typing import Any, List
from collections import OrderedDict
from dataclasses import dataclass, field, fields

from .functions.validation.result import ValidationResult

from angr import SimState
from claripy.ast.bv import BV as BitVector


@dataclass
class ValidationCTX:

    # Restrictions
    # ------------------------------------------------------
    CNSTR_MAP: list = field(default_factory=lambda: [False, True])
    CNSTR_COUNTER: int = 2
    FALSE = 0
    TRUE = 1

    # Lists
    # ------------------------------------------------------
    LIST_MAP: list = field(default_factory=list)
    LIST_COUNTER: int = 0

    # Symbolic states
    # ------------------------------------------------------
    SYM_STATES: dict[int, SimState] = field(default_factory=dict)
    STATE_ID: int = 1

    # Symbolic variables
    # ------------------------------------------------------
    SYM_VARS: OrderedDict[
        str, list[BitVector]
    ] = field(default_factory=OrderedDict)

    # Input Variables
    # ------------------------------------------------------
    INPUT_VARS: list[BitVector] = field(default_factory=list)

    # Return variable
    # ------------------------------------------------------
    RET: Any = None

    # Reached halt_all
    REACHED_NULL: bool = False
    REACHED_HALT: bool = False

    # Stored Restrictions
    STORED_CNSTR: dict = field(default_factory=dict)
    # ------------------------------------------------------

    # Memory
    # ------------------------------------------------------
    # Segments of memory tagged to be evaluated
    # List of tuples: (name, start_addr, nbytes)
    MEMORY_TRIPLES: list = field(default_factory=list)
    MEMORY_SYM_VARS: OrderedDict = field(default_factory=OrderedDict)

    # Validation results
    # ------------------------------------------------------
    # Results of the implications
    # These are supplied to print_counterexamples
    RESULTS: List[ValidationResult] = field(default_factory=list)
    RESULTS_COUNTER: int = 0

    # Logging
    # ------------------------------------------------------
    TEST_COUNT: int = 0
    JSON_LOG: dict = field(default_factory=dict)

    # Path stats
    # ------------------------------------------------------
    SUMM_PATHS: int = 0
    CNCR_PATHS: int = 0

    def reset(self):
        fresh = type(self)()
        for field in fields(self):
            setattr(self, field.name, getattr(fresh, field.name))
