import logging
from abc import ABC, abstractmethod
from typing import Any

from neomodel import config as neomodel_config
from neomodel import db
from sentence_transformers import SentenceTransformer

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"


CYPHER_QUERY = """
CALL db.index.vector.queryNodes('vector_index_MemoryShard_vector_address',\
    $k, $query_vector)
YIELD node, score 
RETURN node.shard_contents AS content, score 
ORDER BY score DESC
"""
logger = logging.getLogger(__name__)


class StoreDB(ABC):
    @abstractmethod
    def configure(self, url: str) -> None:
        pass

    @abstractmethod
    def cypher_query(self, query: str, params: dict[str, Any]) -> tuple[list[Any], Any]:
        pass


class DefaultStoreDB(StoreDB):
    def configure(self, url: str) -> None:
        neomodel_config.DATABASE_URL = url
        db.set_connection(url)

    def cypher_query(self, query: str, params: dict[str, Any]) -> tuple[list[Any], Any]:
        result = db.cypher_query(query, params)
        return result  # type: ignore[no-any-return]


class SummaryStore:
    def __init__(
        self,
        *,
        store_url: str | None = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        override_store: StoreDB | None = None,
    ):
        self.transformer = SentenceTransformer(embedding_model)

        if override_store is not None:
            self.store = override_store
        elif store_url is not None:
            self.store = DefaultStoreDB()
            self.store.configure(store_url)
        else:
            raise ValueError("Must provide store_url or override_store")

    def _vector_search(
        self, query_vector: list[float], k: int = 2
    ) -> list[tuple[str, float]]:
        results, _ = self.store.cypher_query(
            CYPHER_QUERY, {"k": k, "query_vector": query_vector}
        )
        return [
            (shard_with_score[0][9:], shard_with_score[1])
            for shard_with_score in results
        ]

    def _get_embedding(self, text: str) -> list[float]:
        numpy_array = self.transformer.encode(text)
        logger.debug(f"Got embedding of length: {len(numpy_array)}.")
        return numpy_array.tolist()

    def search(self, query: str, k: int = 2) -> list[tuple[str, float]]:
        try:
            vect = self._get_embedding(query)
            return self._vector_search(query_vector=vect, k=k)
        except Exception as e:
            logger.error(f"Failed to retrieve summaries for query {query}", exc_info=e)
            raise RuntimeError(f"Failed to retrieve summaries for query {query}") from e
