import logging

from logging.handlers import  TimedRotatingFileHandler


class LoggingRuntime:
    _instance = None

    FORMAT = "[%(filename)s:%(funcName)s:L%(lineno)d][%(levelname)s](%(asctime)s) %(message)s"
    DTF = "%H:%M:%S"

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self, logger_name:str ="kairix"):

        from rich.console import Console
        from rich.logging import RichHandler

        self.logger = logging.getLogger(logger_name)



        self.console = Console(width=200)
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

        self.file_handler = TimedRotatingFileHandler(
            "logs/kairix.log",
            when="D")

        logging.basicConfig(
            force=True,
            format=LoggingRuntime.FORMAT,
            datefmt= LoggingRuntime.DTF,
            handlers=[self.rich_handler, self.file_handler],
            level="INFO")