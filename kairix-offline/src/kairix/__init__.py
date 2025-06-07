import threading

from dotenv import load_dotenv
from os import getenv
from neomodel import config as neomodel_config
from neomodel import db
from rich.logging import RichHandler
from sentence_transformers import SentenceTransformer
from semchunk import chunkerify
from kairix.types import SourceDocument
import logging
from functools import partial
from transformers import pipeline


__all__ = ['summary_generator', 'LLMTextGenerator',
           'chunker','embedding_transformer', "memory_synth"]

from kairix_core.prompt import system_prompt


def load_llm(model, device):
     return  pipeline(
        "text-generation",
        model=model,
        device_map=device,
        torch_dtype="auto",
        pad_token_id=2,)

def get_or_raise(key: str):
    if getenv(key) is None:
        raise KeyError(f"Missiing required configuration for: {key}")
    return getenv(key)

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


# --------------------------------------------------------------------------------
# Program starts executing  our code here.
# --------------------------------------------------------------------------------
load_dotenv(verbose=True)

FORMAT = "%(message)s"

kairirx_log_stream = InMemoryLogStreamHandler()
logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(), kairirx_log_stream],
)
logger = logging.getLogger("kairix")

logger.info("Initializing Kairix-Offline. V.0.1 - San Francisco, California. Mark Lubin 2025.")


# Setup Neo4j
neomodel_config.DATABASE_URL = get_or_raise("NEO4J_URL")


logger.info("Initialing Neo4J database.")
SourceDocument(
    uid="1", source_label="smoke-test", source_type="none", content="test"
).create_or_update()
db.install_all_labels()


summarizer_model = get_or_raise("KAIRIX_SUMMARIZER_MODEL")
summarizer_device = get_or_raise("KAIRIX_SUMMARIZER_MODEL_DEVICE")
summarizer_batch_size = int(get_or_raise("KAIRIX_SUMMARIZER_BATCH_SIZE"))
summarizer_max_length = int(get_or_raise("KAIRIX_SUMMARIZER_MAX_LENGTH"))
summarizer_system_prompt_key= get_or_raise("KAIRIX_SUMMARIZER_SYSTEM_PROMPT_KEY")


if not hasattr(system_prompt, summarizer_system_prompt_key):
    raise Exception(f"System prompt key '{summarizer_system_prompt_key}' not found.")

summarizer_system_prompt_text  = getattr(system_prompt, summarizer_system_prompt_key)
logger.info("Loaded configuration for summarizer. Initializing Model....This might take time to download firsttime.")

def llm_gen_factory(user_prompt): 
    return summarizer_llm(user_prompt,
                          batch_size=summarizer_batch_size, max_length=summarizer_max_length)
t = threading.Thread(target= lambda _ : load_llm(summarizer_model, summarizer_device))


summarizer_llm = load_llm(summarizer_model, summarizer_device)


if summarizer_llm.tokenizer is None:
    raise Exception(f"No tokenizer found for model -  {summarizer_model}")

summary_generator  =  llm_gen_factory
LLMTextGenerator = llm_gen_factory
chunk_size = int(get_or_raise("KAIRIX_CHUNK_SIZE"))
chunker = chunkerify(summarizer_llm.tokenizer, chunk_size)

embedding_model = get_or_raise("KAIRIX_EMBEDDER_MODEL")
embedding_device = get_or_raise("KAIRIX_EMBEDDER_DEVICE")
embedidng_batch_size = int(get_or_raise("KAIRIX_EMBEDDING_BATCH_SIZE"))
embedding_transformer = SentenceTransformer(embedding_model, device="cpu")


embedding_transformer.encode = partial(
    embedding_transformer.encode,
    batch_size=embedidng_batch_size,
    show_progress_bar=True,
)
memory_synth = SummaryMemorySynth(chunker=chunker,
                                  embedder=embedding_transformer,
                                  llm_text_generator=summary_generator,)
# @
