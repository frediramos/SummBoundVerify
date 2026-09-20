from copy import deepcopy

from pycparser import c_generator
from pycparser.c_ast import TypeDecl

from .generator import ValidationGenerator
from .test import SymbolicTestGen


class SymbolicValidationGenerator(ValidationGenerator):
    """Generates differential symbolic validation tests."""

    @property
    def symbolic(self) -> bool:
        return True

    def functions(self, parsed):
        return parsed.functions

    def gen_headers(self, defs):
        headers = super().gen_headers(defs)
        return headers

    def test_generator(self, args, ret_type, cname, sname):
        return SymbolicTestGen(
            args,
            ret_type,
            cname,
            sname,
            self.memory,
            self.maxnames,
        )
