from summboundverify.exceptions import UnsupportedFloatingPointError

FLOAT_TYPES = frozenset({'float', 'double', 'long double'})


def check_supported(typename: str, where: str) -> None:
    """Raise if the generator cannot build a symbolic value of `typename`."""
    if typename in FLOAT_TYPES:
        raise UnsupportedFloatingPointError(where)
