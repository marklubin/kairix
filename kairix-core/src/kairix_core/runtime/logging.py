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
            format="%(message)s",
            handlers=[
                RichHandler(
                    console=self.console,
                    tracebacks_show_locals=True,
                    rich_tracebacks=True,
                    show_path=True,
                    show_time=True,
                    show_level=True,
                    markup=True
                )],
            level="INFO",
        )
        self.logger = logging.getLogger(logger_name)
