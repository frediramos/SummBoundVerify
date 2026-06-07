from pathlib import Path

from summboundverify.utils.summary import FunctionType


class ValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class GenError(ValidationError):
    pass


class RunError(ValidationError):
    pass


class TimeoutError(RunError):
    def __init__(self, timeout: int):
        message = (
            f"Validation run timed out after {timeout} seconds.\n"
            "The code may contain an infinite loop or otherwise non-terminating execution."
        )
        super().__init__(message)


class InvalidSymbolicVariableSizeError(Exception):
    def __init__(self, length):
        message = (
            f"Cannot create a symbolic variable with size: {length}. "
            "Size in bits must be divisible by 8."
        )
        super().__init__(message)


class UnsatConstraintError(Exception):
    def __init__(self, function: str, constraint):
        message = (
            f"Unsatisfiable constraint passed to '{function}' function.\n"
            f"Constraint: {constraint}"
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


class DuplicateFunctionsError(GenError):
    def __init__(self, name: str, file: Path):
        message = f"Multiple functions named '{name}' in file: {file}"
        super().__init__(message)
