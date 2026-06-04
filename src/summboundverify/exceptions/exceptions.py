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
            f"Validation run timed out after {timeout} seconds. "
            "The code may contain an infinite loop or otherwise non-terminating execution."
        )
        super().__init__(message)


class CompilationError(GenError):
    def __init__(self, stderr: str, cmd: str):
        self.cmd = cmd
        message = (
            "Could not compile the validation test."
            f"Stderr:\n{stderr}"
        )
        super().__init__(message)
