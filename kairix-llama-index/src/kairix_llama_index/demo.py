"""Simple RAG chatbot with transparent memory injection via Ollama template."""

from typing import TYPE_CHECKING

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.llms import LLM
from llama_index.core.memory import SimpleComposableMemory
from llama_index.core.retrievers import BaseRetriever
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.neo4jvector import Neo4jVectorStore

if TYPE_CHECKING:
    from llama_index.core.schema import NodeWithScore

# Configuration
EMBEDDING_MODEL: str = "sentence-transformers/all-mpnet-base-v2"
INFERENCE_MODEL: str = "q3-sum:latest"
OLLAMA_BASE_URL: str = "https://ollama.kairix.net"
NEO4J_URL: str = "bolt://cayucos.thrush-escalator.ts.net:7687"


vector_store: Neo4jVectorStore = Neo4jVectorStore(
    url=NEO4J_URL,
    username="neo4j",
    password="password",
    index_name="memoryshard_vector_index",
    node_label="MemoryShard",
    text_node_property="shard_contents",
    embedding_node_property="vector_address",
    embedding_dimension=1536,
)

index: VectorStoreIndex = VectorStoreIndex.from_vector_store(
    vector_store,
    storage_context=StorageContext.from_defaults(vector_store=vector_store),
    embed_model=HuggingFaceEmbedding(model_name=EMBEDDING_MODEL),
)


# Create custom chat engine that injects memories
class MemoryInjectedChatEngine(SimpleChatEngine):
    def __init__(self, llm: LLM, index: VectorStoreIndex):
        super().__init__(llm, SimpleComposableMemory.from_defaults(), [])
        self.retriever: BaseRetriever = retriever

    def chat(
        self, message: str, chat_history: list[ChatMessage] | None = None
    ) -> ChatResponse:
        # Retrieve memories based on current message
        nodes: list[NodeWithScore] = self.retriever.retrieve(message)
        memories: str = "\n".join([f"[{n.score:.2f}] {n.text}" for n in nodes])

        # Update LLM's memories field dynamically
        self.llm._additional_kwargs["memories"] = memories

        # Call parent chat method
        return super().chat(message, chat_history)


# Initialize components
llm: Ollama = Ollama(
    model=INFERENCE_MODEL,
    base_url=OLLAMA_BASE_URL,
    request_timeout=120.0,
    additional_kwargs={"memories": ""},  # Placeholder
)

retriever: BaseRetriever = index.as_retriever(similarity_top_k=5)

# Create chat engine
chat_engine: MemoryInjectedChatEngine = MemoryInjectedChatEngine(
    llm=llm, retriever=retriever
)

# Start REPL
print("🤖 RAG Chatbot Ready! (type 'exit' to quit)")
print("💭 Memories will be transparently injected via Ollama template.\n")
chat_engine.chat_repl()
