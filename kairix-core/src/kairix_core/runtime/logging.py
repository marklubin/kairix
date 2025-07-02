import logging
import os
from imaplib import Response_code
from logging import Handler, FileHandler


class LoggingRuntime:
    _instance = None

    FORMAT = "[%(filename)s:%(funcName)s:L%(lineno)d][%(levelname)s](%(asctime)s) %(message)s"
    DTF = "%H:%M:%S"

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self, logger_name:str ="kairix"):
        import logging

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

        logging.basicConfig(
            force=True,
            format=LoggingRuntime.FORMAT,
            datefmt= LoggingRuntime.DTF,
            handlers=[self.rich_handler],
            level="INFO")


        self.wirelog = self._init_wirelog()



    def _init_wirelog(self):

        def request(message, *args):
            logger.info(f"""
            HTTP REQUEST BODY>
            
                {message}
            
            
            """)

        def response(message, args):
            logger.info(F"""
            HTTP RESPONSE BODY>
            
            {message}

            
        """)
        logger = logging.getLogger("kairix-server-wirelog")
        logger.setLevel("DEBUG")
        logger.request = request
        logger.response = response

        return logger
