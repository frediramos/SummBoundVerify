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

    # Heap
    # ------------------------------------------------------
    HEAP_CHUNKS: dict = field(default_factory=dict)

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

    # What the run learned, kept past the per-test reset
    # ------------------------------------------------------
    # STORED_CNSTR is wiped between tests so they cannot contaminate each
    # other, which also means the formulas are gone by the time run() returns.
    # They are worth keeping: the one stored under `summ_testN` is the
    # summary's path condition and symbolic return, which is exactly what a
    # sampling check needs -- so a `both` run need not compute it twice.
    CONSTRAINTS: dict = field(default_factory=dict)

    # Fields reset() leaves alone: they outlive a single test by design.
    PRESERVED = frozenset({'CONSTRAINTS'})

    def archive(self):
        '''Keep this test's formulas before the reset takes them.'''
        self.CONSTRAINTS.update(self.STORED_CNSTR)

    def reset(self):
        fresh = type(self)()
        for field in fields(self):
            if field.name in self.PRESERVED:
                continue
            setattr(self, field.name, getattr(fresh, field.name))
