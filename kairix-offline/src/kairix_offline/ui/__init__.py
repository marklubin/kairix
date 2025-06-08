import logging
import os

from dotenv import load_dotenv
from kairix_core.util.logging import InMemoryLogStreamHandler
from rich.logging import RichHandler

from kairix_offline.processing import initialize_processing

# Only load dotenv if not in test environment
if "PYTEST_CURRENT_TEST" not in os.environ:
    load_dotenv(verbose=True)

    initialize_processing()

FORMAT = "%(message)s"

kairirx_log_stream = InMemoryLogStreamHandler()
logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(), kairirx_log_stream],
)
logger = logging.getLogger("kairix_offline")

logger.info(
    "Initializing Kairix-Offline. V.0.1 - San Francisco, California. Mark Lubin 2025."
)
