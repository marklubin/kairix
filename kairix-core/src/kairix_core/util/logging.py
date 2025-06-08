import logging

kairix_logger_format_str = "%(message)s"


class InMemoryLogStreamHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.buffer = ""

    def emit(self, record: logging.LogRecord) -> None:
        self.buffer += f"""
        \n|{record.filename}::{record.funcName}::L{record.lineno}[{record.levelname}]({record.created})\
            {record.getMessage()}
        """

    def stream_logs(self):
        yield self.buffer
