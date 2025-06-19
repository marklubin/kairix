from threading import Thread

from kairix_core.util.logging import InMemoryLogStreamHandler


class LogStreamingThreadRuner:
    def __init__(self, log_handler: InMemoryLogStreamHandler, thread: Thread):
        self._log_handler = log_handler
        self._thread = thread

    def start(self):
        self._log_handler.clear()
        self._thread.start()

        while self._thread.is_alive():
            yield self._log_handler.buffered_logs()
            self._thread.join(1)
