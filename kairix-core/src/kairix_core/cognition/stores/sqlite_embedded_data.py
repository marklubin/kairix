"""
SQLite-based embedded data store with vector search capabilities.

This module replaces the Neo4j-based EmbeddedDataStore with a SQLite implementation
that uses SQLite-VSS for vector similarity search.
"""
import logging
from typing import Any, Callable, Optional, Iterable, List, Tuple

from sentence_transformers import SentenceTransformer

from kairix_core.runtime.storage import StorageRuntime
from kairix_core.types.db import Entity, MemoryShard

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

ContentWithScore = Tuple[Any, float]


class SQLiteEmbeddedDataStore:
    """SQLite-based store for vector-indexed data with similarity search."""
    
    def __init__(
        self,
        *,
        table_name: str,  # 'entity' or 'memory_shard'
        content_key: str,  # field to return in search results
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        embedding_dims: int = 768,
        content_transform: Optional[Callable[[Any], Any]] = None,
        storage: Optional[StorageRuntime] = None,
    ):
        """
        Initialize the embedded data store.
        
        Args:
            table_name: Name of the table to search ('entity' or 'memory_shard')
            content_key: Field name to return in search results
            embedding_model: Name of the sentence transformer model
            embedding_dims: Dimensions of the embedding vectors
            content_transform: Optional function to transform content before returning
            storage: Optional StorageRuntime instance (creates new if not provided)
        """
        self.transformer = SentenceTransformer(
            embedding_model, truncate_dim=embedding_dims
        )
        
        self.storage = storage or StorageRuntime()
        self.vector_dao = self.storage.vector_dao
        
        self.table_name = table_name
        self.content_key = content_key
        self.content_transform = content_transform
        self.embedding_dims = embedding_dims
        
        # Map table names to model classes
        self.model_class = Entity if table_name == 'entity' else MemoryShard
    
    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        numpy_array = self.transformer.encode(text)
        logger.debug(f"Got embedding of length: {len(numpy_array)}.")
        return numpy_array.tolist()
    
    def _vector_search(
        self, query_vector: List[float], k: int = 2, agent_id: Optional[int] = None
    ) -> Iterable[ContentWithScore]:
        """
        Perform vector similarity search.
        
        Args:
            query_vector: Query embedding vector
            k: Number of results to return
            agent_id: Optional agent ID filter (only for memory_shard)
            
        Returns:
            Iterator of (content, score) tuples
        """
        if self.table_name == 'entity':
            results = self.vector_dao.search_similar_entities(query_vector, limit=k)
        else:  # memory_shard
            results = self.vector_dao.search_similar_memories(
                query_vector, limit=k, agent_id=agent_id
            )
        
        # Fetch the actual objects and extract content
        with self.storage.session() as session:
            dao = self.storage.get_dao(self.model_class, session)
            
            for obj_id, distance in results:
                obj = dao.get_by_id(obj_id)
                if obj:
                    # Extract the requested content field
                    content = getattr(obj, self.content_key)
                    
                    if self.content_transform:
                        content = self.content_transform(content)
                    
                    # Convert distance to similarity score (inverse)
                    score = 1.0 / (1.0 + distance)
                    yield content, score
    
    def search(
        self, query: str, k: int = 2, agent_id: Optional[int] = None
    ) -> Iterable[ContentWithScore]:
        """
        Search for similar content based on text query.
        
        Args:
            query: Text query to search for
            k: Number of results to return
            agent_id: Optional agent ID filter (only for memory_shard)
            
        Returns:
            Iterator of (content, score) tuples
        """
        try:
            vect = self._get_embedding(query)
            return self._vector_search(query_vector=vect, k=k, agent_id=agent_id)
        except Exception as e:
            logger.error(f"Failed to search for query: {query}", exc_info=e)
            raise RuntimeError(f"Failed to search for query: {query}") from e
    
    def add_item_with_embedding(
        self, item_id: int, text_content: str, embedding: Optional[List[float]] = None
    ) -> None:
        """
        Add or update an item's embedding in the vector index.
        
        Args:
            item_id: ID of the entity or memory shard
            text_content: Text to generate embedding from (if embedding not provided)
            embedding: Optional pre-computed embedding vector
        """
        if embedding is None:
            embedding = self._get_embedding(text_content)
        
        if self.table_name == 'entity':
            self.vector_dao.add_entity_embedding(item_id, embedding)
        else:
            self.vector_dao.add_memory_embedding(item_id, embedding)


# Factory functions to match the Neo4j store initialization patterns
def create_memory_shard_store(storage: Optional[StorageRuntime] = None) -> SQLiteEmbeddedDataStore:
    """Create an embedded store for memory shards."""
    return SQLiteEmbeddedDataStore(
        table_name='memory_shard',
        content_key='contents',  # Return the shard contents
        embedding_dims=128,
        storage=storage
    )


def create_concept_store(storage: Optional[StorageRuntime] = None) -> SQLiteEmbeddedDataStore:
    """Create an embedded store for entities (concepts)."""
    return SQLiteEmbeddedDataStore(
        table_name='entity',
        content_key='semantic_id',  # Return the semantic ID
        embedding_dims=128,
        storage=storage
    )