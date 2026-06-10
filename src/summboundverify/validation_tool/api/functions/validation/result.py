from abc import ABC, abstractmethod

from claripy.ast.bv import BV as BitVector

from z3 import (
    ExprRef,
    Solver,
    Not,
    sat
)

from .utils import ValidationModel, CorrectnessProperty


class ValidationResult(ABC):
    """
    Validation result objects
    """

    def __init__(
        self,
        result: CorrectnessProperty,
        summ: ExprRef,
        cncrt: ExprRef,
        ignore_vars: set[BitVector]
    ):
        self._result = result
        self.summ = summ
        self.cncrt = cncrt
        self.ignore = ignore_vars

    def __str__(self):
        return self._result.value

    def __eq__(self, other):
        return self._result == other

    @abstractmethod
    def implication(self) -> str:
        pass

    @abstractmethod
    def result(self) -> str:
        pass

    @abstractmethod
    def simple_result(self) -> str:
        pass

    @abstractmethod
    def models(self) -> ValidationModel:
        pass


class Exact(ValidationResult):
    def __init__(self, summ, cncrt, vars):
        super().__init__(CorrectnessProperty.exact, summ, cncrt, vars)

    def implication(self):

        impl = (
            'Summary ^ ~Cncrt_Function: unsat\n'
            'Cncrt_Function ^ ~Summary: unsat\n'
            'Summary -> Cncrt_Function ^ Cncrt_Function -> Summary'
        )

        return impl

    def result(self):
        res = 'Summary and Concrete function are exact'
        return res

    def simple_result(self):
        return self._result.value

    def models(self):
        return ValidationModel()


class Under(ValidationResult):
    def __init__(self, summ, cncrt, vars):
        super().__init__(CorrectnessProperty.under, summ, cncrt, vars)

    def implication(self):
        impl = (
            'Summary ^ ~Cncrt_Function: unsat\n'
            'Cncrt_Function ^ ~Summary: sat\n'
            'Summary -> Cncrt_Function'
        )

        return impl

    def result(self):
        res = 'Summary under-approximates the concrete function'
        return res

    def simple_result(self):
        return self._result.value

    # Create solver to generate models
    # Missing path

    def _create_solver(self):
        solver = Solver()

        solver.add(Not(self.summ))
        solver.add(self.cncrt)
        return solver

    def models(self):
        solver = self._create_solver()
        assert solver.check() == sat
        model = solver.model()
        return ValidationModel(missing=model)


class Over(ValidationResult):
    def __init__(self, summ, cncrt, vars):
        super().__init__(CorrectnessProperty.over, summ, cncrt, vars)

    def implication(self):

        impl = (
            'Summary ^ ~Cncrt_Function: sat\n'
            'Cncrt_Function ^ ~Summary: unsat\n'
            'Cncrt_Function -> Summary'
        )

        return impl

    def result(self):
        res = 'Summary over-approximates the concrete function'
        return res

    def simple_result(self):
        return self._result.value

    # Create solver to generate models
    # Wrong path

    def _create_solver(self):
        solver = Solver()

        solver.add(self.summ)
        solver.add(Not(self.cncrt))
        return solver

    def models(self):
        solver = self._create_solver()
        assert solver.check() == sat
        model = solver.model()
        return ValidationModel(wrong=model)


class Unkown(ValidationResult):
    def __init__(self, summ, cncrt, vars):
        super().__init__(CorrectnessProperty.bug, summ, cncrt, vars)

    def implication(self):

        impl = (
            'Summary ^ ~Cncrt_Function: sat\n'
            'Cncrt_Function ^ ~Summary: sat'
        )

        return impl

    def result(self):
        res = 'Summary is (buggy) not an over/under-approximation of the concrete function'
        return res

    def simple_result(self):
        return self._result.value

    # Create solver to generate models
    def _create_solvers(self):

        # Missing path
        solver1 = Solver()
        solver1.add(Not(self.summ))
        solver1.add(self.cncrt)

        # Wrong path
        solver2 = Solver()
        solver2.add(self.summ)
        solver2.add(Not(self.cncrt))

        return (solver1, solver2)

    def models(self):
        solver_missing, solver_wrong = self._create_solvers()

        assert solver_missing.check() == sat
        missing = solver_missing.model()

        assert solver_wrong.check() == sat
        wrong = solver_wrong.model()

        return ValidationModel(missing=missing, wrong=wrong)
