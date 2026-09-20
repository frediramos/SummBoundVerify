import json
import time

from pathlib import Path
from angr import SimulationManager

from .macros import SYM_VAR
from .api import ValidationAPI


def get_states(sm: SimulationManager):
    states = sm.deadended + sm.active
    return states


def save_paths(
    paths_dir: Path,
    binary_name: str,
    sm: SimulationManager,
):
    paths_dir.mkdir(parents=True, exist_ok=True)

    for idx, state in enumerate(get_states(sm)):
        file = paths_dir / f"{binary_name}_{idx}.path"

        variables = [
            var
            for var in state.solver.all_variables
            if SYM_VAR in str(var)
        ]

        with open(file, 'a') as f:
            for var in variables:
                value = state.solver.eval(var)
                f.write(f"{value}\n")


def _execution_stats(
    *,
    time_spent: float | None,
    timeout: int | None,
    start: float | None,
    exception: Exception | None,
) -> dict:

    if exception is not None:
        assert start is not None
        return {
            "exception": f"{type(exception)}:{exception}",
            "time": round(time.monotonic() - start, 4),
        }

    if timeout is not None:
        return {"time": f"timeout:{timeout}"}

    assert time_spent is not None
    return {"time": time_spent}


def save_stats(
    stats_dir: Path,
    binary_name: str,
    sm: SimulationManager,
    api: ValidationAPI,
    fcalled: dict[str, int],
    *,
    time_spent: float | None = None,
    timeout: int | None = None,
    start: float | None = None,
    exception: Exception | None = None,
):
    stats_dir.mkdir(parents=True, exist_ok=True)

    stats = _execution_stats(
        time_spent=time_spent,
        timeout=timeout,
        start=start,
        exception=exception,
    )

    stats["paths"] = (
        {
            "summary": api.ctx.SUMM_PATHS,
            "concrete": api.ctx.CNCR_PATHS,
        }
        if api.ctx.SUMM_PATHS
        else len(get_states(sm))
    )

    fcalled.pop("main", None)
    stats["called"] = fcalled

    path = stats_dir / f"{binary_name}_stats.json"

    with open(path, "w") as f:
        json.dump({binary_name: stats}, f, indent=2)
