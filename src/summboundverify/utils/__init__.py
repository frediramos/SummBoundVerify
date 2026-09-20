from enum import Enum


class DescribedEnum(Enum):
    def __new__(cls, value, _):
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, _, desc):
        self.desc = desc