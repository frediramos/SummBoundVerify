from importlib.resources import files


class Files:
    api = "API.md"


def api(text=False):
    resources = files("summboundverify.resources")
    api = resources / Files.api
    if text:
        return api.read_text()
    return api
