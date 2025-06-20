import logging
from rich.console import Console
from rich.logging import RichHandler


import transformers.utils.logging as t_logging

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
                    show_path=True,
                    show_time=True,
                    show_level=True,
                    markup=True
                )

        logging.basicConfig(
            force=True,
            format="%(message)s",
            handlers=[self.rich_handler],
            level="INFO",

        )

        self.logger = logging.getLogger(logger_name)
        self.logger.propagate = True

        t_logging.set_verbosity_info()
        t_logging._get_library_root_logger().addHandler(self.rich_handler)
