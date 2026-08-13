import os
import json

from pathlib import Path
from tempfile import mkstemp, gettempdir


def current_file(file: str | Path) -> Path:
    return Path(file).resolve()


def current_dir(file: str | Path) -> Path:
    return current_file(file).parent


def read_file(path: str | Path) -> str:
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {p}") from e

    return text


def read_file_lines(path: str | Path) -> list[str]:
    text = read_file(path)
    return text.splitlines()


def write_file(file: str | Path, contents: str, mkdir: bool = True) -> Path:
    path = Path(file)
    try:
        if mkdir:
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        return path
    except OSError as e:
        raise OSError(f"Failed to write to {path}: {e}") from e


def remove_file(file: str | Path, missing_ok: bool = True) -> None:
    path = Path(file)
    try:
        path.unlink()
    except FileNotFoundError as e:
        if not missing_ok:
            raise FileNotFoundError(f"File not found: {path}") from e
    except OSError as e:
        raise OSError(f"Failed to remove file {path}: {e}") from e


def tmp_file(suffix='') -> Path:
    """Return a Path in the system temporary directory with a unique name."""
    fd, name = mkstemp(suffix=suffix)
    os.close(fd)
    return Path(name)


def tmp_dir() -> Path:
    """Retutn the Path to the /tmp directory"""
    tmp = gettempdir()
    return Path(tmp)


def dump_json(file: str | Path, obj, indent=2):
    json_str = json.dumps(obj, indent=indent, ensure_ascii=False)
    write_file(file, json_str)


def fake_libc_path():
    path = current_dir(__file__) / "fake_libc_include"
    if not path.is_dir():
        err = "Could not locate pycparser fake_libc_include"
        raise RuntimeError(err)
    return path
