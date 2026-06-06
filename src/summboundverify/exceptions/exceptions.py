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


class CompilationError(GenError):
    def __init__(self, stderr: str, cmd: str):
        self.cmd = cmd
        message = (
            "Could not compile the validation test.\n"
            f"Stderr:\n{stderr}"
        )
        super().__init__(message)


class ArgumentMismatchError(GenError):
    def __init__(self, summ_args: list, cncrt_args: list):
        self.summ_args = summ_args
        self.cncrt_args = cncrt_args
        message = "Summary and concrete function arguments do not match.\n"
        super().__init__(message)
