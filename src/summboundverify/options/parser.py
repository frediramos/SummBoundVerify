import logging

from .options import Options

logger = logging.getLogger(__name__)


def parse_config_file(conf: str) -> dict:
    """Parse a YAML configuration file.

    Returns a dict whose keys are Option names and whose values are
    the parsed configuration values.
    """
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required for config file support: pip install pyyaml"
        )

    with open(conf) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        return {}

    config: dict = {}
    for key, value in data.items():
        key = str(key)
        if key in Options:
            config[key] = value
        else:
            logger.error("[!] Unknown option '%s' in %s", key, conf)

    return config
