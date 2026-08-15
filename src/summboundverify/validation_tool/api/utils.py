from claripy.ast.bv import BV as BitVector


class SymbString:
    """
    A Symbolic String representation.
    Can contain concrete characters and/or symbolic bytes.
    """

    def __init__(self, init: str | list | None = None):
        self._string = [] if init is None else list(init)

    def __str__(self) -> str:
        chars = []

        for char in self._string:
            if isinstance(char, str):
                chars.append(char)
            elif isinstance(char, BitVector):
                raise ValueError(
                    "Cannot convert symbolic string containing "
                    "symbolic bytes to a Python string"
                )
            else:
                raise TypeError(
                    f"Invalid character type: {type(char).__name__}")

        return ''.join(chars)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._string!r})"

    def __len__(self) -> int:
        return len(self._string)

    def __getitem__(self, index):
        return self._string[index]

    def __iter__(self):
        return iter(self._string)

    def __contains__(self, item) -> bool:
        return item in self._string

    def __bool__(self) -> bool:
        return bool(self._string)

    def __eq__(self, other) -> bool:
        if isinstance(other, SymbString):
            return self._string == other._string

        if isinstance(other, str):
            try:
                return str(self) == other
            except ValueError:
                return False

        return NotImplemented

    def __add__(self, other):
        if isinstance(other, SymbString):
            other = other._string
        elif isinstance(other, str):
            other = list(other)
        else:
            return NotImplemented

        return SymbString(self._string + other)

    def __radd__(self, other):
        if isinstance(other, str):
            return SymbString(list(other) + self._string)

        return NotImplemented

    def __iadd__(self, other):
        if isinstance(other, SymbString):
            self._string.extend(other._string)
        elif isinstance(other, str):
            self._string.extend(other)
        else:
            return NotImplemented

        return self
