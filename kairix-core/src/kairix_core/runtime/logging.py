import logging
from rich.console import Console
from rich.logging import RichHandler


import transformers.utils.logging as t_logging
FORMAT = "[%(filename)s:%(funcName)s:L%(lineno)d][%(levelname)s](%(asctime)s) %(message)s"
DTF = "%H:%M:%S"

class LoggingRuntime:
    _instance = None


    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self, logger_name:str ="kairix"):
        self.console = Console(width=140)
        self.rich_handler = RichHandler(
                    console=self.console,
                    tracebacks_show_locals=True,
                    rich_tracebacks=True,
                    show_path=False,
                    show_time=False,
                    show_level=False,
                    markup=True,
                    enable_link_path=True,
                )


        logging.basicConfig(
            force=True,
            format=FORMAT,
            datefmt= DTF,
            handlers=[self.rich_handler],
            level="INFO",
        )

        self.logger = logging.getLogger(logger_name)
        t_logging.set_verbosity_warning()
