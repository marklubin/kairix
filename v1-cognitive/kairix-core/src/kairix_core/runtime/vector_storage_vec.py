"""
SQLite Vec integration for vector embeddings.

This module provides vector search capabilities for Entity and MemoryShard embeddings
using sqlite-vec extension (no FAISS dependency).

Note: Requires sqlite-vec to be installed:
    pip install sqlite-vec
"""
from typing import List, Tuple, Optional, Union
import sqlite_vec
from sqlite_vec import serialize_float32
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger


def enable_sqlite_vec(engine: Engine) -> None:
    """
    Enable sqlite-vec extension for the database engine.
    
    This needs to be called after creating the engine but before using vector search.
    Vector search is now mandatory, so this will raise an exception if vec cannot be loaded.
    """
    def load_vec_for_connection(dbapi_conn):
        try:
            # Enable loading extensions
            dbapi_conn.enable_load_extension(True)
            
            # Load vec extension
            dbapi_conn.execute("SELECT load_extension(?)", [sqlite_vec.loadable_path()])
            
            # Disable loading extensions for security
            dbapi_conn.enable_load_extension(False)
            
            logger.info("sqlite-vec extension loaded successfully")
        except Exception as e:
            raise RuntimeError(
                f"Failed to load sqlite-vec extension (vector search is required): {e}\n"
                "Please ensure sqlite-vec is installed. You can install it with:\n"
                "  pip install sqlite-vec\n"
                "Or follow instructions at: https://github.com/asg017/sqlite-vec"
            )
    
    # Register event listener for future connections
    @event.listens_for(engine, "connect")
    def load_vec(dbapi_conn, connection_record):
        load_vec_for_connection(dbapi_conn)
    
    # Load for existing connections in the pool
    with engine.connect() as conn:
        load_vec_for_connection(conn.connection.dbapi_connection)


def create_vec_tables(engine: Engine) -> None:
    """
    Create tables for vector similarity search using sqlite-vec.
    
    Creates vec tables for:
    - entity_vec: For Entity embeddings
    - memory_shard_vec: For MemoryShard embeddings
    
    Raises RuntimeError if vec tables cannot be created.
    """
    with engine.connect() as conn:
        try:
            # Create vec table for Entity embeddings
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS entity_vec (
                    id INTEGER PRIMARY KEY,
                    embedding FLOAT[768]
                );
            """))
            
            # Create vec table for MemoryShard embeddings  
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS memory_shard_vec (
                    id INTEGER PRIMARY KEY,
                    embedding FLOAT[768]
                );
            """))
            
            conn.commit()
            logger.info("vec tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create vec tables: {e}")
            raise RuntimeError(
                f"Failed to create vec tables (vector search is required): {e}\n"
                "This usually means the vec extension is not properly loaded."
            )


class VectorSearchDAO:
    """Data Access Object for vector similarity search operations using sqlite-vec."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
    
    def add_entity_embedding(self, entity_id: int, embedding: Union[List[float], str]) -> None:
        """Add or update an entity embedding in the vec index."""
        with self.engine.connect() as conn:
            # Convert to proper format if needed
            if isinstance(embedding, str):
                # Already in JSON format, sqlite-vec accepts this
                embedding_data = embedding
            else:
                # Convert list to binary format for efficiency
                embedding_data = serialize_float32(embedding)
            
            conn.execute(text("""
                INSERT OR REPLACE INTO entity_vec (id, embedding)
                VALUES (:id, :embedding)
            """), {"id": entity_id, "embedding": embedding_data})
            conn.commit()
    
    def add_memory_embedding(self, memory_id: int, embedding: Union[List[float], str]) -> None:
        """Add or update a memory shard embedding in the vec index."""
        with self.engine.connect() as conn:
            # Convert to proper format if needed
            if isinstance(embedding, str):
                # Already in JSON format, sqlite-vec accepts this
                embedding_data = embedding
            else:
                # Convert list to binary format for efficiency
                embedding_data = serialize_float32(embedding)
            
            conn.execute(text("""
                INSERT OR REPLACE INTO memory_shard_vec (id, embedding)
                VALUES (:id, :embedding)
            """), {"id": memory_id, "embedding": embedding_data})
            conn.commit()
    
    def search_similar_entities(self, query_embedding: List[float], limit: int = 10) -> List[Tuple[int, float]]:
        """
        Search for similar entities based on embedding similarity.
        
        Args:
            query_embedding: The embedding vector to search for
            limit: Maximum number of results to return
            
        Returns:
            List of (entity_id, distance) tuples ordered by similarity
        """
        # Validate limit
        if limit is None or limit <= 0:
            logger.warning(f"Invalid limit {limit} for vector search, using default limit=5")
            limit = 5
            
        with self.engine.connect() as conn:
            # Convert query to binary format
            query_binary = serialize_float32(query_embedding)
            
            result = conn.execute(text("""
                SELECT id, vec_distance_L2(embedding, :query) as distance
                FROM entity_vec
                WHERE embedding IS NOT NULL
                ORDER BY distance
                LIMIT :limit
            """), {"query": query_binary, "limit": limit})
            
            return [(row[0], row[1]) for row in result]
    
    def search_similar_memories(self, query_embedding: List[float], limit: int = 10, 
                              agent_id: Optional[int] = None) -> List[Tuple[int, float]]:
        """
        Search for similar memory shards based on embedding similarity.
        
        Args:
            query_embedding: The embedding vector to search for
            limit: Maximum number of results to return
            agent_id: Optional filter by agent ID
            
        Returns:
            List of (memory_id, distance) tuples ordered by similarity
        """
        # Validate limit
        if limit is None or limit <= 0:
            logger.warning(f"Invalid limit {limit} for memory search, using default limit=5")
            limit = 5
            
        with self.engine.connect() as conn:
            logger.debug(f"search_similar_memories called with limit={limit}, agent_id={agent_id}")
            
            # Convert query to binary format
            query_binary = serialize_float32(query_embedding)
            
            if agent_id:
                # Filter by agent_id by joining with memory_shards table
                result = conn.execute(text("""
                    SELECT v.id, vec_distance_L2(v.embedding, :query) as distance
                    FROM memory_shard_vec v
                    JOIN memory_shards m ON v.id = m.id
                    WHERE v.embedding IS NOT NULL
                    AND m.agent_id = :agent_id
                    ORDER BY distance
                    LIMIT :limit
                """), {"query": query_binary, "limit": limit, "agent_id": agent_id})
            else:
                result = conn.execute(text("""
                    SELECT id, vec_distance_L2(embedding, :query) as distance
                    FROM memory_shard_vec
                    WHERE embedding IS NOT NULL
                    ORDER BY distance
                    LIMIT :limit
                """), {"query": query_binary, "limit": limit})
            
            return [(row[0], row[1]) for row in result]
    
    def bulk_add_entity_embeddings(self, embeddings: List[Tuple[int, Union[List[float], str]]]) -> None:
        """Bulk add entity embeddings for efficiency."""
        with self.engine.connect() as conn:
            for entity_id, embedding in embeddings:
                # Convert to proper format if needed
                if isinstance(embedding, str):
                    embedding_data = embedding
                else:
                    embedding_data = serialize_float32(embedding)
                
                conn.execute(text("""
                    INSERT OR REPLACE INTO entity_vec (id, embedding)
                    VALUES (:id, :embedding)
                """), {"id": entity_id, "embedding": embedding_data})
            conn.commit()
    
    def remove_entity_embedding(self, entity_id: int) -> None:
        """Remove an entity from the vec index."""
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM entity_vec WHERE id = :id"), {"id": entity_id})
            conn.commit()
    
    def remove_memory_embedding(self, memory_id: int) -> None:
        """Remove a memory shard from the vec index."""
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM memory_shard_vec WHERE id = :id"), {"id": memory_id})
            conn.commit()