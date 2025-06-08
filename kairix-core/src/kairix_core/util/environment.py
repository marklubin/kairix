from os import getenv


def get_or_raise(key: str):
    if getenv(key) is None:
        raise KeyError(f"Missing required configuration for: {key}")
    return getenv(key)
