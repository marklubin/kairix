import logging
from logging.handlers import  TimedRotatingFileHandler

from kairix_core.util.utils import get_or_raise


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


        username = get_or_raise("KAIRIX_USER_NAME")
        app_id = get_or_raise("KAIRIX_APP_ID")
        log_level = get_or_raise("KAIRIX_LOG_LEVEL")

        logfile = f"../logs/{username}/{app_id}.log"

        self.file_handler = TimedRotatingFileHandler(
            logfile,
            when="D")

        logging.basicConfig(
            force=True,
            format=LoggingRuntime.FORMAT,
            datefmt= LoggingRuntime.DTF,
            handlers=[self.rich_handler, self.file_handler],
            level=log_level)