import sys
import time
import signal
import logging

from pathlib import Path

from angr import (
    BP_AFTER,
    options,
    Project,
    SimHeapPTMalloc,
    SimState,
    SimulationManager,
)

from summboundverify.exceptions import TimeoutError

from .api import ValidationAPI
from .api.functions.files.fs import SymbolicFS

from .stats import save_paths, save_stats

logger = logging.getLogger(__name__)


class AngrEngine:
    def __init__(
        self,
        binary: str | Path,
        timeout: int | None = 30 * 60,
        results_dir: str | Path = ".",
        stats_dir: str | Path | None = None,
        paths_dir: str | Path | None = None,
        convert_ascii: bool = False,
        ignore: str | Path | None = None,
    ):
        self.binary = Path(binary)
        self.binary_name = self.binary.name

        self.timeout = timeout

        self.results_dir = Path(results_dir)
        self.stats_dir = Path(stats_dir) if stats_dir else None
        self.paths_dir = Path(paths_dir) if paths_dir else None

        self.convert_ascii = convert_ascii
        self.ignore_list = self._ignore_list(ignore)

        self.fcalled: dict[str, int] = {}

        self.api: ValidationAPI

    @property
    def constraints(self) -> dict:
        '''The formulas this run built, by the name the test stored them under.
        '''
        api = getattr(self, 'api', None)
        if api is None:
            return {}

        return {**api.ctx.CONSTRAINTS, **api.ctx.STORED_CNSTR}

    @staticmethod
    def _ignore_list(ignore: str | Path | None) -> list[str]:
        if not ignore:
            return []
        with open(ignore) as f:
            return [line.strip() for line in f]

    def _set_hooks(self, project: Project, sm: SimulationManager):
        self.api = ValidationAPI(
            project=project,
            sm=sm,
            binary=self.binary_name,
            out=self.results_dir,
            convert=self.convert_ascii,
        )
        self.api.hook_api()

    def _create_entry_state(self, project: Project) -> SimState:
        state_options = {
            options.TRACK_SOLVER_VARIABLES,
            options.ZERO_FILL_UNCONSTRAINED_MEMORY,
            options.ZERO_FILL_UNCONSTRAINED_REGISTERS,
        }

        state = project.factory.entry_state(
            mode="symbolic",
            add_options=state_options,
        )

        state.register_plugin("heap", SimHeapPTMalloc())
        state.register_plugin("fs", SymbolicFS())

        state.libc.simple_strtok = False  # type: ignore

        if self.stats_dir:
            state.inspect.b(
                "call",
                when=BP_AFTER,
                action=self._count_fcall,
            )

        return state

    def _count_fcall(self, state: SimState):
        address = state.inspect.function_address  # type: ignore
        if address is None:
            return

        address = state.solver.eval(address, cast_to=int)
        symbol = self.project.loader.find_symbol(address)

        if symbol is not None:
            self.fcalled[symbol.name] = self.fcalled.get(symbol.name, 0) + 1

    def _register_timeout(self, sm: SimulationManager):
        if self.timeout is None:
            return

        def handler(signum, frame):
            if self.stats_dir:
                save_stats(
                    self.stats_dir,
                    self.binary_name,
                    sm,
                    self.api,
                    self.fcalled,
                    timeout=self.timeout,
                )

            logger.error("Timeout detected: %s seconds", self.timeout)
            raise TimeoutError(self.timeout)  # type: ignore

        signal.signal(signal.SIGALRM, handler)
        signal.alarm(self.timeout)

    @staticmethod
    def _unregister_timeout():
        signal.alarm(0)

    def step(self, sm: SimulationManager, start: float):
        try:
            while sm.active:
                sm.step()
        except Exception as e:
            if self.stats_dir:
                save_stats(
                    self.stats_dir,
                    self.binary_name,
                    sm,
                    self.api,
                    self.fcalled,
                    start=start,
                    exception=e,
                )
            raise
        finally:
            self._unregister_timeout()

    def run(self):
        sys.setrecursionlimit(20_000)

        project = Project(
            self.binary,
            exclude_sim_procedures_list=self.ignore_list,
        )

        self.project = project

        state = self._create_entry_state(project)
        sm = project.factory.simulation_manager(state)

        self._register_timeout(sm)
        self._set_hooks(project, sm)

        start = time.monotonic()
        self.step(sm, start)
        elapsed = round(time.monotonic() - start, 4)

        if self.stats_dir:
            save_stats(
                self.stats_dir,
                self.binary_name,
                sm,
                self.api,
                self.fcalled,
                time_spent=elapsed,
            )

        if self.paths_dir:
            save_paths(self.paths_dir, self.binary_name, sm)
