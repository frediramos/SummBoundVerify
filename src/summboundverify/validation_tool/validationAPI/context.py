from typing import Any
from collections import OrderedDict
from dataclasses import dataclass, field


@dataclass
class ValidationCTX:

    # Restrictions
    # ------------------------------------------------------
    CNSTR_MAP: list = field(default_factory=list)
    CNSTR_COUNTER: int = 0

    # Symbolic states
    # ------------------------------------------------------
    SYM_STATES: dict = field(default_factory=dict)
    STATE_ID: int = 1

    # Symbolic variables
    # ------------------------------------------------------
    SYM_VARS: OrderedDict = field(default_factory=OrderedDict)

    # Input Variables
    # ------------------------------------------------------
    INPUT_VARS: list = field(default_factory=list)

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
    RESULTS: list = field(default_factory=list)
    RESULTS_COUNTER: int = 0

    # Logging
    # ------------------------------------------------------
    TEST_COUNT: int = 0
    JSON_LOG: dict = field(default_factory=dict)

    # Path stats
    # ------------------------------------------------------
    SUMM_PATHS: int = 0
    CNCR_PATHS: int = 0
