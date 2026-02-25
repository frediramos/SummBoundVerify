SimulationManager = None

Settings = {
    'binary_path': None,
    'binary_name': None,
    'results_dir': None,
    'stats': False,
    'convert_chars': False,
    'timeout': 30*60
}

Stats = {
    'time_spent': 0,
    'f_called': {},
    'f_names': None
}


def set_SimManager(sm):
    global SimulationManager
    SimulationManager = sm


def get_SimManager():
    global SimulationManager
    return SimulationManager


def set_config(*args):
    for arg in args:
        key, value = arg
        Settings[key] = value


def get_config(*args):
    values = []
    for arg in args:
        if arg in Settings.keys():
            v = Settings[arg]
            values.append(v)
        else:
            values.append(None)
    return values


def set_stats(*args):
    for arg in args:
        key, value = arg
        Stats[key] = value


def get_stats(*args):
    values = []
    for arg in args:
        if arg in Stats.keys():
            v = Stats[arg]
            values.append(v)
        else:
            values.append(None)
    return values
