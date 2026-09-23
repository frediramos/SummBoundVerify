"""Argument specification for SBV validation.

An argspec file describes each function argument's semantic role and
constraints so the test generator knows which tagging calls to emit,
how to size symbolic arrays, and how to bound numeric values.

See ``ARGSPEC.md`` at the repository root for the full schema reference.
"""

import yaml
from pathlib import Path

VALID_SEMANTICS = ('scalar', 'memory', 'file')
VALID_MEMORY_TYPES = ('read', 'write')
VALID_FILE_TYPES = ('descriptor', 'pointer', 'name')

_SEMANTIC_KEYS = {'scalar', 'memory', 'file'}
_GENERIC_KEYS = {'type', 'semantic', 'nullbytes', 'default', 'concretearray'}
_ALLOWED_TOP_KEYS = _GENERIC_KEYS | _SEMANTIC_KEYS


def load_argspec(path: str | Path | None) -> dict:
    """
    Load an argspec YAML file and return a validated dict keyed by arg name.
    Returns an empty dict when *path* is None or the file is absent.
    """
    if path is None:
        return {}

    path = Path(path)
    if not path.exists():
        return {}

    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        return {}

    spec: dict = {}
    for name, attrs in data.items():
        if not isinstance(attrs, dict):
            attrs = {}
        name = str(name)
        _validate_arg(name, attrs)
        spec[name] = attrs

    return spec


def _validate_arg(name: str, attrs: dict) -> None:
    """Validate a single argument's spec and reject unknown or stale keys."""
    unknown = set(attrs) - _ALLOWED_TOP_KEYS
    if unknown:
        raise ValueError(
            f"argspec '{name}': unknown keys {unknown}. "
            f"Allowed: {sorted(_ALLOWED_TOP_KEYS)}"
        )

    semantic = attrs.get('semantic', 'scalar')
    if semantic not in VALID_SEMANTICS:
        raise ValueError(
            f"argspec '{name}': invalid semantic '{semantic}'. "
            f"Must be one of {VALID_SEMANTICS}"
        )

    if semantic == 'memory':
        _validate_memory(name, attrs.get('memory', {}))
    elif semantic == 'file':
        _validate_file(name, attrs.get('file', {}))
    elif semantic == 'scalar':
        _validate_scalar(name, attrs.get('scalar', {}))

    extra_blocks = _SEMANTIC_KEYS - {semantic}
    for key in extra_blocks:
        if key in attrs:
            raise ValueError(
                f"argspec '{name}': has '{key}' block but semantic "
                f"is '{semantic}'"
            )


def _validate_memory(name: str, mem: dict) -> None:
    if not isinstance(mem, dict):
        raise ValueError(
            f"argspec '{name}': 'memory' must be a mapping"
        )
    allowed = {'type', 'size'}
    unknown = set(mem) - allowed
    if unknown:
        raise ValueError(
            f"argspec '{name}.memory': unknown keys {unknown}"
        )
    mtype = mem.get('type', 'write')
    if mtype not in VALID_MEMORY_TYPES:
        raise ValueError(
            f"argspec '{name}.memory': invalid type '{mtype}'. "
            f"Must be one of {VALID_MEMORY_TYPES}"
        )


def _validate_file(name: str, fspec: dict) -> None:
    if not isinstance(fspec, dict):
        raise ValueError(
            f"argspec '{name}': 'file' must be a mapping"
        )
    allowed = {'type', 'fname', 'data'}
    unknown = set(fspec) - allowed
    if unknown:
        raise ValueError(
            f"argspec '{name}.file': unknown keys {unknown}"
        )
    ftype = fspec.get('type', 'descriptor')
    if ftype not in VALID_FILE_TYPES:
        raise ValueError(
            f"argspec '{name}.file': invalid type '{ftype}'. "
            f"Must be one of {VALID_FILE_TYPES}"
        )
    for sub in ('fname', 'data'):
        if sub in fspec:
            _validate_file_data(name, sub, fspec[sub])


def _validate_file_data(name: str, key: str, spec: dict) -> None:
    if not isinstance(spec, dict):
        raise ValueError(
            f"argspec '{name}.file.{key}': must be a mapping"
        )
    allowed = {'symbolic', 'size'}
    unknown = set(spec) - allowed
    if unknown:
        raise ValueError(
            f"argspec '{name}.file.{key}': unknown keys {unknown}"
        )


def _validate_scalar(name: str, sc: dict) -> None:
    if not isinstance(sc, dict):
        raise ValueError(
            f"argspec '{name}': 'scalar' must be a mapping"
        )
    allowed = {'maxvalue'}
    unknown = set(sc) - allowed
    if unknown:
        raise ValueError(
            f"argspec '{name}.scalar': unknown keys {unknown}"
        )


def has_memory_output(argspec: dict) -> bool:
    """Whether the spec includes any memory arg that is written to."""
    for attrs in argspec.values():
        if attrs.get('semantic') == 'memory':
            mem = attrs.get('memory', {})
            if mem.get('type', 'write') == 'write':
                return True
    return False


def extract_constraints(argspec: dict) -> dict:
    """Extract per-arg constraints from argspec into generator parameters.

    Returns a dict whose keys match ``ValidationGenerator`` constructor
    parameter names.  Only keys with actual values are included so the
    caller can fall back to defaults for anything the argspec does not
    specify.
    """
    if not argspec:
        return {}

    result: dict = {}

    arraysizes: list = []
    nullbytes_list: list = []
    maxnum: list = []
    maxnames: list = []
    defaults: dict = {}
    concretes: dict = {}

    for i, (name, spec) in enumerate(argspec.items(), 1):
        semantic = spec.get('semantic', 'scalar')

        if semantic == 'memory':
            mem = spec.get('memory', {})
            if 'size' in mem:
                arraysizes.append(mem['size'])

        elif semantic == 'scalar':
            sc = spec.get('scalar', {})
            if 'maxvalue' in sc:
                maxnum.append(sc['maxvalue'])
                maxnames.append(name)

        if 'nullbytes' in spec:
            nullbytes_list.append(spec['nullbytes'])

        if 'default' in spec:
            defaults[i] = spec['default']

        if 'concretearray' in spec:
            concretes[i] = spec['concretearray']

    if arraysizes:
        if len(arraysizes) == 1:
            result['arraysize'] = arraysizes
        else:
            result['arraysize'] = [arraysizes]

    if nullbytes_list:
        if len(nullbytes_list) == 1:
            result['nullbytes'] = nullbytes_list
        else:
            result['nullbytes'] = [nullbytes_list]

    if maxnum:
        result['maxnum'] = maxnum
        result['maxnames'] = maxnames

    if defaults:
        result['defaults'] = [defaults]

    if concretes:
        result['concrete_arrays'] = [concretes]

    return result
