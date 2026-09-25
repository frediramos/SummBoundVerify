from .generator import ValidationGenerator
from .test import SummaryFuzzTestGen, ConcreteFuzzTestGen

from .utils import Macros, define_macro


class SummaryFuzzGenerator(ValidationGenerator):
    """Generates symbolic tests for the summary used by fuzzing."""

    @property
    def symbolic(self) -> bool:
        return True

    def functions(self, parsed):
        return parsed.summary_functions

    def test_generator(self, args, ret_type, _, summ_name):
        return SummaryFuzzTestGen(
            args,
            ret_type,
            summ_name,
            self.maxnames,
            argspec=self.argspec,
        )


class ConcreteFuzzGenerator(ValidationGenerator):
    """Generates native tests for the concrete function used by fuzzing."""

    @property
    def symbolic(self) -> bool:
        return False

    def functions(self, parsed):
        return parsed.concrete_functions

    # Fuzzing does not need the symbolic API/type stubs.
    def gen_headers(self, _):
        headers = [
            "#include <fcntl.h>",
            "#include <unistd.h>",
            "#include <stdio.h>",
            "#include <sys/types.h>",
            "",
        ]
        headers += self.gen_macros(Macros.ARRAY_SIZE, self.arraysize)
        headers += self.gen_macros(Macros.MAX_NUM, self.maxnum)
        headers += self.gen_file_macros(self.argspec)
        return headers

    def test_generator(self, args, ret_type, cncrt_name, _):
        return ConcreteFuzzTestGen(
            args,
            ret_type,
            cncrt_name,
            self.maxnames,
            argspec=self.argspec,
        )
