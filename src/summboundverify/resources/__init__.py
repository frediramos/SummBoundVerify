from importlib.resources import files


class Files:
    api = "API.md"


def resources():
    return files(__package__)


def api(text=False):
    api = resources() / Files.api
    if text:
        return api.read_text()
    return api
