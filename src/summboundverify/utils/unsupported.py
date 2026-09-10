"""Types the test generator refuses to draw a symbolic value for.

There is one entry, and the reason it is a refusal rather than a limitation
is that the failure it replaces was silent. `symbolic` is a pointer-sized
integer, so `double x = sym_var_named("x", 64)` compiles: the drawn value is
*converted* to a double instead of being reinterpreted as one. The generated
test then runs, samples nothing but integer-valued doubles -- never 0.5,
never NaN, never an infinity -- and reports a verdict as confidently as any
other run. A `FILE *` argument, by contrast, has always failed at build time,
and that is why it needs no entry here.

Checked at generation time on purpose, so a target is refused once for both
engines rather than skipped by one and mis-sampled by the other.
"""

from summboundverify.exceptions import UnsupportedTypeError

FLOAT_TYPES = frozenset({'float', 'double', 'long double'})


def check_supported(typename: str, where: str) -> None:
    """Raise if the generator cannot build a symbolic value of `typename`.

    `where` names the position for the error message -- "argument 'x'",
    "return type", "field 'point.dx'" -- since the type alone rarely says
    enough to find it in the source.
    """
    if typename in FLOAT_TYPES:
        raise UnsupportedTypeError(typename, where)
