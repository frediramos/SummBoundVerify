from pathlib import Path
from typing import TYPE_CHECKING

from pycparser.c_parser import ParseError

# Defer heavy imports
if TYPE_CHECKING:
    from claripy import ClaripyError

from summboundverify.utils.summary import FunctionType


class ValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class GenError(ValidationError):
    pass


class RunError(ValidationError):
    pass

# -----------------------------------------------------------------------------------
# Run Exceptions
# -----------------------------------------------------------------------------------


class TimeoutError(RunError):
    def __init__(self, timeout: int):
        message = (
            f"Validation run timed out after {timeout} seconds.\n"
            "The code may contain an infinite loop or otherwise non-terminating execution."
        )
        super().__init__(message)


class InvalidSymbolicVariableSizeError(RunError):
    def __init__(self, length):
        message = (
            f"Cannot create a symbolic variable with {length} bits. "
            "Size in bits must be divisible by 8."
        )
        super().__init__(message)


class InvalidArchVariableSizeError(RunError):
    def __init__(self, length, arch):
        message = (
            f"Cannot create a symbolic variable with {length} bits. "
            f"We are using a {arch}-bit arch."
        )
        super().__init__(message)


class UnsatConstraintError(RunError):
    def __init__(self, function: str, constraint):
        message = (
            f"Unsatisfiable constraint passed to '{function}' function.\n"
            f"Constraint: {constraint}"
        )
        super().__init__(message)


class AssertConstraintError(RunError):
    def __init__(self, constraint):
        message = (
            f"The constraint: '{constraint}' does not hold.\n"
            f"I.e., the current path condition does not imply such constraint."
        )
        super().__init__(message)


class ClaripyConstraintError(RunError):
    def __init__(
        self,
        claripy_function: str,
        claripy_exception: 'ClaripyError',
        caller: str | None = None,
    ):
        message = f"Error in Claripy function '{claripy_function}'.\n"

        if caller:
            message += f"Called from C function '{caller}'.\n"

        message += (
            "The Claripy backend reported the following error:\n"
            f"{claripy_exception}"
        )

        super().__init__(message)


class DuplicateSymbolicVariableError(RunError):
    def __init__(self, name: str):
        message = (
            f"A symbolic variable named '{name}' already exists.\n"
            "Each named symbolic variable must have a unique name; use a "
            "different name or 'sym_var', which generates a unique name "
            "automatically."
        )
        super().__init__(message)


class MemoryPermissionsError(RunError):
    def __init__(self, addr, ptr, size):
        message = (
            f"The memory address: '{addr}' does not have R/W permission.\n"
            f"This check was called on pointer '{ptr}' and the next {size} bytes."
        )
        super().__init__(message)


class ReportError(RunError):
    def __init__(self, file, line, msg):
        message = (
            f"Runtime error detected in '{file}' at line {line}:\n"
            f"{msg}"
        )
        super().__init__(message)


class InvalidOpenFlagError(RunError):
    def __init__(self, flag):
        message = (
            f"Unsupported file open flag: '{flag}'\n"
        )
        super().__init__(message)


class InvalidArgumentError(RunError):
    argument: str

    def __init__(self, function: str, value):
        message = (
            f"The function '{function}' takes only concrete "
            f"'{self.argument}' values.\n"
            f"Invalid argument found: {value}"
        )
        super().__init__(message)


class UnsatFSError(RunError):
    def __init__(self):
        message = "The symbolic file system is in an unsat state."
        super().__init__(message)


class SymbolicPointerError(InvalidArgumentError):
    argument = "pointer"


class InvalidFdError(InvalidArgumentError):
    argument = "file descriptor"


class InvalidFpError(InvalidArgumentError):
    argument = "file pointer (FILE*)"


class InvalidCountError(InvalidArgumentError):
    argument = "count"


class InvalidOffsetError(InvalidArgumentError):
    argument = "offset"


class InvalidSizeError(InvalidArgumentError):
    argument = "size"


class InvalidPointerError(InvalidArgumentError):
    argument = "pointer"


class InvalidModeError(InvalidArgumentError):
    argument = "mode_t"


class InvalidFlagsError(InvalidArgumentError):
    argument = "open flags"


# -----------------------------------------------------------------------------------
# Generation Exceptions
# -----------------------------------------------------------------------------------


class FileParseError(GenError):
    def __init__(self, file: str | Path, pycparser_error: ParseError):
        self.file = file
        err = str(pycparser_error)
        message = (
            f"'pycparser' could not parse the C file: {file}.\n"
            f"Error:\n{err}"
        )
        super().__init__(message)


class CompilationError(GenError):
    def __init__(self, stderr: str, cmd: str):
        self.cmd = cmd
        self.stderr = stderr
        message = (
            "Could not compile the validation test.\n"
            f"Stderr:\n{stderr}"
        )
        super().__init__(message)


class ArgumentMismatchError(GenError):
    def __init__(self, cncrt_args, summ_args):
        self.cncrt_args = cncrt_args
        self.summ_args = summ_args
        message = "Summary and concrete function arguments do not match.\n"
        super().__init__(message)


class ReturnMismatchError(GenError):
    def __init__(self, cncrt_ret, summ_ret):
        self.cncrt_ret = cncrt_ret
        self.summ_ret = summ_ret
        message = "Summary and concrete function return types do not match.\n"
        super().__init__(message)


class MissingFunctionError(GenError):
    def __init__(self, ftype: FunctionType, file: Path, fname: str | None = None):
        if fname:
            message = f"No {ftype.value} with name '{fname}' found in file: {file}"
        else:
            message = f"No {ftype.value} found in file: {file}"
        super().__init__(message)


class MultipleFunctionsError(GenError):
    def __init__(self, ftype: FunctionType, file: Path):
        message = (
            "No function name provided.\n"
            f"There should be only one function in the {ftype.value} file: {file}"
        )
        super().__init__(message)


class DuplicateFunctionDefinitionError(GenError):
    def __init__(self, name: str, file: Path):
        message = f"Multiple functions named '{name}' defined in file: {file}"
        super().__init__(message)


class DuplicateFunctionDeclarationError(GenError):
    def __init__(self, name: str, file: Path):
        message = f"Multiple functions named '{name}' declared in file: {file}"
        super().__init__(message)


class UnsupportedFloatingPointError(GenError):
    def __init__(self, location: str):
        self.location = location
        message = (
            f"Floating point values are unsupported.\n"
            f"Floating point found in {location}"
        )
        super().__init__(message)
