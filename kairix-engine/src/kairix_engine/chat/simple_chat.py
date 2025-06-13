from collections.abc import Generator

from neomodel import config as neomodel_config
from neomodel import db
from ollama import ChatResponse, Client, Message
from rich import pretty
from rich.console import Console
from sentence_transformers import SentenceTransformer
from smolagents import InferenceClientModel, ToolCallingAgent

NEO4J_URL = "bolt://neo4j:password@cayucos.thrush-escalator.ts.net:7687"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

OLLAMA_MODEL = "q3-runtime"

console = Console()
console.print("[cyan] Initializing.....")

pretty.install()


inference_model = InferenceClientModel(EMBEDDING_MODEL)


class Neo4jMemoryStore:
    neomodel_config.DATABASE_URL = NEO4J_URL

    _CYPHER_QUERY = """
    CALL db.index.vector.queryNodes('vector_index_MemoryShard_vector_address',\
        $k, $query_vector)
    YIELD node, score 
    RETURN node.shard_contents AS content, score 
    ORDER BY score DESC
    """

    def __init__(self, embedder: SentenceTransformer):
        self.embedder = embedder

    def _vector_search(self, query_vector: list[float], k: int = 2):
        results, _ = db.cypher_query(
            Neo4jMemoryStore._CYPHER_QUERY, {"k": k, "query_vector": query_vector}
        )
        return [
            (shard_with_score[0][9:], shard_with_score[1])
            for shard_with_score in results
        ]

    def _get_embedding(self, message: str) -> list[float]:
        numpy_array = self.embedder.encode(message)
        console.log(f"Got embedding of length: {len(numpy_array)}.")
        return numpy_array.tolist()

    def search(self, query: str):
        vect = self._get_embedding(query)
        return self._vector_search(query_vector=vect)


class SimpleChat:
    def __init__(self):
        self.history: list[Message] = []
        self.memory_store = Neo4jMemoryStore(SentenceTransformer(EMBEDDING_MODEL))

        self.memory_perception_agent = ToolCallingAgent(
            model=inference_model, Tools=[self.memory_store.search]
        )

        self.ollama = Client()

    def submit(self, content: str) -> Message:
        recollections = self._remember(content)
        user_message = Message(role="user", content=content + recollections)

        self.history.append(user_message)

        console.print(user_message.content)

        response = self.ollama.chat(
            model=OLLAMA_MODEL, messages=self.history, stream=False, think=True
        )
        assert type(response) is ChatResponse
        assistant_message = response.message
        assert response.message is not None

        self.history.append(assistant_message)

        return assistant_message

    def stream(self, content: str) -> Generator:
        Message(role="user", content=content)
        pass
