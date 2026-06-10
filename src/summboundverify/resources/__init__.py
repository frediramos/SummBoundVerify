from importlib.resources import files


class Files:
    full_api = "full-API.md"
    gen_api = "gen-API.md"


def resources():
    return files(__package__)


def full_api():
    api = resources() / Files.full_api
    return api.read_text()


def gen_api():
    api = resources() / Files.gen_api
    return api.read_text()
