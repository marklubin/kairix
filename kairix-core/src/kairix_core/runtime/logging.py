import logging
from rich.console import Console
from rich.logging import RichHandler



class LoggingRuntime:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self, logger_name:str ="kairix"):
        self.console = Console(width=140)
        logging.basicConfig(
            handlers=[RichHandler(console=self.console, rich_tracebacks=True, markup=True)],
            level="INFO",
        )
        self.logger = logging.getLogger(logger_name)
