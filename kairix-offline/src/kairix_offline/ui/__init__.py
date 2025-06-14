import logging
import os
from os import getenv

from dotenv import load_dotenv
from kairix_core.util.logging import InMemoryLogStreamHandler, Neo4jLogHandler
from rich.logging import RichHandler

from kairix_offline.processing import initialize_processing

# Only load dotenv if not in test environment
if "PYTEST_CURRENT_TEST" not in os.environ:
    load_dotenv(verbose=True)
    initialize_processing()


if os.getenv("KAIRIX_DEBUG"):
    import pdb

    pdb.set_trace()

FORMAT = "%(message)s"

kairirx_log_stream = InMemoryLogStreamHandler()
logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(), Neo4jLogHandler(), kairirx_log_stream],
)
logger = logging.getLogger("kairix_offline")

logger.info(
    "Initializing Kairix-Offline. V.0.1 - San Francisco, California. Mark Lubin 2025."
)
