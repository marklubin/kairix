import logging
import uuid

from kairix_core.types import StoredLog

kairix_logger_format_str = "%(message)s"


class InMemoryLogStreamHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.buffer = []

    def emit(self, record: logging.LogRecord) -> None:
        self.buffer.append(f"""\
            {record.filename}::{record.funcName}::L{record.lineno}[{record.levelname}]({record.created})\
            {record.getMessage()})
            """)

    def clear(self):
        self.buffer = []

    def buffered_logs(self):
        return "\n".join(self.buffer)


class Neo4jLogHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record: logging.LogRecord) -> None:
        if "kairix" not in record.module:
            return
        try:
            uid = str(uuid.uuid4())
            StoredLog(
                uid=uid,
                level=record.levelname,
                source=f"{record.filename}::{record.funcName}::L{record.lineno}",
                message=record.getMessage(),
                details={
                    "pathname": record.pathname,
                    "module": record.module,
                    "thread": record.threadName,
                    "process": record.processName,
                },
            ).save()
        except Exception:
            self.handleError(record)
