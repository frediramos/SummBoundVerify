import json
from dataclasses import dataclass, field, asdict

from ...context import ValidationCTX

from .utils import CorrectnessProperty
from .models import PrettyModel
from .result import ValidationResult

type Model = dict[str, str | int | Model]


@dataclass
class ValidationJSON:
    result: str
    npaths: int
    counterexamples: Model = field(default_factory=dict)


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
            f"==> Summary Constraints: \n\n\t{summ}\n\n"
            f"==> Existencial Variables: \n\t{ignore}\n\n"
            f"==> Result: {result}\n\n"
        )

        if result != CorrectnessProperty.exact:

            counterexamples = "==> Counterexamples: \n\n"
            missing_ = f"Missing path example: \n{missing}\n\n\n"
            wrong_ = f"Wrong path example: \n{wrong}\n\n\n"

            if result == CorrectnessProperty.under:
                counterexamples += missing_

            elif result == CorrectnessProperty.over:
                counterexamples += wrong_

            else:
                counterexamples += missing_
                counterexamples += wrong_
        else:
            counterexamples = ""

        log = header + counterexamples

        return log.rstrip()

    def pretty_model(
        self,
        ctx: ValidationCTX,
        ignore: list[str],
        convert: bool
    ) -> PrettyModel:

        pm = PrettyModel(
            input_vars=ctx.SYM_VARS,
            mem_vars=ctx.MEMORY_SYM_VARS,
            ret=ctx.RET,
            ignore=ignore,
            convert_chars=convert
        )
        return pm

    def _to_dict(self, obj: ValidationJSON):
        data = asdict(obj)
        return data

    def _to_json(self, obj: ValidationJSON):
        data = self._to_dict(obj)
        json_str = json.dumps(data, indent=2)
        return json_str

    def _add_counterexample(
        self,
        obj: ValidationJSON,
        t: CorrectnessProperty,
        model: Model
    ):
        obj.counterexamples[t.value] = model

    def json_result(
        self,
        ctx: ValidationCTX,
        ignore: list[str],
        convert: bool
    ):

        result = self.result
        models = self.models

        result_str = result.simple_result()
        npaths = ctx.SUMM_PATHS

        obj = ValidationJSON(result=result_str, npaths=npaths)
        pm = self.pretty_model(ctx, ignore, convert)

        if self.result == CorrectnessProperty.bug:
            missing = models.missing
            wrong = models.wrong

            p_missing = pm.prettify(missing)
            p_wrong = pm.prettify(wrong)

            self._add_counterexample(obj, CorrectnessProperty.over, p_missing)
            self._add_counterexample(obj, CorrectnessProperty.under, p_wrong)

        elif self.result == CorrectnessProperty.under:
            missing = models.missing
            p_missing = pm.prettify(missing)
            self._add_counterexample(obj, CorrectnessProperty.over, p_missing)

        elif self.result == CorrectnessProperty.over:
            wrong = models.wrong
            p_wrong = pm.prettify(wrong)
            self._add_counterexample(obj, CorrectnessProperty.under, p_wrong)

        return self._to_dict(obj)
