import inspect

from functools import cache
from pathlib import Path

from angr import Project, SimulationManager

from summboundverify.api import PREFIX, all_stubs, required_stubs

from .context import ValidationCTX
from .functions import constraints
from .functions import lists
from .functions import solver
from .functions import heap
from .functions.files import functions as files
from .functions.validation import functions as validation

from .functions.validation.functions import halt_all, print_counterexamples


class ValidationAPI:
    def __init__(
        self,
        project: Project,
        sm: SimulationManager,
        binary: str,
        out: str | Path,
        convert: bool
    ):
        self.prefix = PREFIX
        self.ctx = ValidationCTX()

        # Dynamic args
        self.sm = sm
        self.out = out
        self.project = project
        self.binary = binary
        self.convert = convert

        # Hooks that require arguments
        self.arg_hooks = [
            (halt_all, self.sm),
            (print_counterexamples, self.sm, self.binary, self.out, self.convert)
        ]

        self._check_sra_implemented()

    def _add_prefix(self, functions: set[str]) -> set[str]:
        preffixed = set()
        for func in functions:
            if not func.startswith(self.prefix) and not func.startswith('_'):
                func = self.prefix + func
            preffixed.add(func)
        return preffixed

    @cache
    def _implemented(self):
        impl = {}
        for module in (solver, validation, heap, constraints, lists, files):
            for name, cls in inspect.getmembers(module, inspect.isclass):
                if cls.__module__ != module.__name__:
                    continue

                if inspect.isabstract(cls):
                    continue

                impl[name] = cls

        return impl

    def _check_missing(
        self,
        available: set[str],
        required: set[str],
        err: str,
    ) -> None:
        missing = required - available
        if missing:
            raise RuntimeError(f"{err}: {missing}")

    def _check_sra_hooked(self, hooked: set[str]) -> None:
        err = "The following required API functions are not hooked"
        self._check_missing(
            self._add_prefix(hooked),
            set(required_stubs()),
            err
        )

    def _check_sra_implemented(self) -> None:
        err = "The following API functions are not implemented"
        self._check_missing(
            self._add_prefix(set(self._implemented())),
            set(all_stubs()),
            err
        )

    def _hook(self, name: str, summary, *args):
        hook_name = name

        if not name.startswith("_"):
            hook_name = self.prefix + name

        summary = summary(self.ctx, *args)

        if self.project.loader.find_symbol(hook_name):
            self.project.hook_symbol(hook_name, summary)

        return hook_name

    def _hook_with_args(self):
        hooked = set()
        for func in self.arg_hooks:
            f = func[0]
            args = func[1:]
            name = f.__name__
            hook = self._hook(name, f, *args)
            hooked.add(hook)
        return hooked

    def hook_api(self):
        implemented = self._implemented()
        hooked = set(self._hook_with_args())

        for name, cls in implemented.items():

            if len(inspect.signature(cls).parameters) > 1:
                continue

            hook = self._hook(name, cls)
            hooked.add(hook)

        self._check_sra_hooked(hooked)
