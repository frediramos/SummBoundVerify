from dataclasses import dataclass, field

from .result import ValidationResult

type Model = dict[str, str | int | Model]

@dataclass
class CounterExamples:
    under_approximation: Model = field(default_factory=dict)
    over_approximation: Model = field(default_factory=dict)


@dataclass
class ValidationJSON:
    result: str
    npaths: int
    counterexamples: CounterExamples


class ValidationOutput():
    def __init__(self, result: ValidationResult):
        self.result = result
        self.models = result.models()

    def text_log(self) -> str:
        result = self.result
        models = self.models

        cncrt = result.cncrt
        summ = result.summ

        missing = models.missing
        wrong = models.wrong
        
        if len(ignore := result.ignore) == 0:
            ignore = 'Empty Set'

        header = (
            "===================== Result =====================\n\n"
            f"==> Concrete Constraints: \n\n\t{cncrt}\n\n"
            f"==> Concrete Constraints: \n\n\t{summ}\n\n"
            f"==> Existencial Variables: \n\t{ignore}\n\n"
            f"==> Result: {result}\n\n"
        )

        if result != 'exact':

            counterexamples = "==> Counterexamples: \n\n"
            missing_ = f"Missing path example: \n{missing}\n\n\n"
            wrong_ = f"Wrong path example: \n{wrong}\n\n\n"

            if result == 'under':
                counterexamples += missing_

            elif result == 'over':
                counterexamples += wrong_

            else:
                counterexamples += missing_
                counterexamples += wrong_
        else:
            counterexamples = ""

        log = header + counterexamples

        return log.rstrip()
