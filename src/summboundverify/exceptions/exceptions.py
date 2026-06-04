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