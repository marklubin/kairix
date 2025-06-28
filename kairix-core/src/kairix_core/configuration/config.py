
from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="KAIRIX",
    settings_files=['settings.toml', '.secrets.toml'],
    environments=True
)
