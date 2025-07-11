import logging
import os
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

        self.file_handler = None
        self.logger = logging.getLogger(logger_name)



        log_level = os.getenv("KAIRIX_LOG_LEVEL") or "DEBUG"


        # Create a simple console handler with our format
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(fmt=LoggingRuntime.FORMAT, datefmt=LoggingRuntime.DTF))
        
        handlers = [console_handler, self.file_handler] if self.file_handler else [console_handler]

        logging.basicConfig(
            force=True,
            format=LoggingRuntime.FORMAT,
            datefmt=LoggingRuntime.DTF,
            handlers=handlers,
            level=log_level)


    def setup_logfile(self):
        if os.getenv("KAIRIX_USE_LOG_FILE"):
            username = os.getenv("KAIRIX_USER_NAME") or "default"
            app_id = os.getenv("KAIRIX_APP_ID") or "default"

            log_dir = f"/var/kairix/logs/{username}"
            logfile = f"{log_dir}/{app_id}.log"

            try:
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                    print(f"[LoggingRuntime] Created log directory: {log_dir}")
                else:
                    print(f"[LoggingRuntime] Log directory already exists: {log_dir}")

                self.file_handler = TimedRotatingFileHandler(
                    logfile,
                    when="D"
                )
                print(f"[LoggingRuntime] Log file set up at: {logfile}")

            except Exception as e:
                print(f"[LoggingRuntime] Failed to set up log file at {logfile}: {e}")
