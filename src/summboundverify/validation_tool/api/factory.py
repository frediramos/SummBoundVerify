import inspect

from pathlib import Path

from angr import Project, SimulationManager

from .context import ValidationCTX
from .functions import solver
from .functions import constraints
from .functions import lists
from .functions.validation import functions

from .functions.validation.functions import halt_all, print_counterexamples


class ValidationAPI():
    def __init__(self, project: Project, sm: SimulationManager):
        self.project = project
        self.sm = sm
        self.ctx = ValidationCTX()

    def _hook_with_args(self, binary, out, ascci):

        self.project.hook_symbol(
            halt_all.__name__, halt_all(self.ctx, self.sm)
        )

        self.project.hook_symbol(
            print_counterexamples.__name__,
            print_counterexamples(self.ctx, self.sm, binary, out, ascci)
        )

    def _hook(self, symbol: str, summary):
        summary = summary(self.ctx)
        if self.project.loader.find_symbol(symbol):
            self.project.hook_symbol(symbol, summary)

    def hook_api(
        self,
        binary_name: str,
        out: str | Path,
        convert_ascii=False
    ):
        self._hook_with_args(binary_name, out, convert_ascii)

        for t in (solver, functions, constraints, lists):

            for name, cls in inspect.getmembers(t, inspect.isclass):

                if cls.__module__ != t.__name__:
                    continue

                if inspect.isabstract(cls):
                    continue

                args = inspect.signature(cls).parameters
                if len(args) > 1:
                    continue

                self._hook(name, cls)
