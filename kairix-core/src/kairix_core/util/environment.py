from os import getenv


def get_or_raise(key: str) -> str:
    value = getenv(key)
    if value is None:
        raise KeyError(f"Missing required configuration for: {key}")
    return value
