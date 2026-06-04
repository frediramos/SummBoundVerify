from enum import Enum
from typing import Optional
from dataclasses import dataclass

from z3 import ModelRef


class CorrectnessProperty(Enum):
    under = "under-approximation"
    over = "over-approximation"
    exact = "exact"
    bug = "unknown (bug)"


@dataclass
class ValidationModel():
    missing: Optional[ModelRef] = None
    wrong: Optional[ModelRef] = None


def bit_is_set(num, bit):
    bit = int('1' + '0'*bit, 2)
    return num & bit != 0


def to_signed_char(number):
    if bit_is_set(number, 8-1):
        number = -(-number & 0xFF)
    return number


def to_signed_int(number):
    if bit_is_set(number, 32-1):
        number = -(-number & 0xFFFFFFFF)
    return number


def to_signed_long(number):
    if bit_is_set(number, 64-1):
        number = -(-number & 0xFFFFFFFFFFFFFFFF)
    return number
