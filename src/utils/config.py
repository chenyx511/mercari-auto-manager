import os
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml')

_config = None


def load_config() -> dict:
    global _config
    if _config is None:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            _config = yaml.safe_load(f)
    return _config


def reload_config() -> dict:
    global _config
    _config = None
    return load_config()


def save_config(config: dict):
    global _config
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    _config = config


def get(key: str, default=None):
    config = load_config()
    keys = key.split('.')
    value = config
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default
        if value is None:
            return default
    return value
