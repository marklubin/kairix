"""
SQLite VSS (Vector Similarity Search) integration for vector embeddings.

This module provides vector search capabilities for Entity and MemoryShard embeddings
using SQLite-VSS extension.

Note: Requires sqlite-vss to be installed:
    pip install sqlite-vss
"""
from typing import List, Tuple, Optional
import json
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger


def enable_sqlite_vss(engine: Engine) -> None:
    """
    Enable SQLite VSS extension for the database engine.
    
    This needs to be called after creating the engine but before using vector search.
    Vector search is now mandatory, so this will raise an exception if VSS cannot be loaded.
    """
    def load_vss_for_connection(dbapi_conn):
        try:
            # Enable loading extensions
            dbapi_conn.enable_load_extension(True)
            
            # Load VSS using the sqlite_vss module
            import sqlite_vss
            # First load vector0, then vss0
            sqlite_vss.load(dbapi_conn)
            
            # Disable loading extensions for security
            dbapi_conn.enable_load_extension(False)
            
            logger.info("SQLite VSS extension loaded successfully")
        except Exception as e:
            raise RuntimeError(
                f"Failed to load SQLite VSS extension (vector search is required): {e}\n"
                "Please ensure sqlite-vss is installed. You can install it with:\n"
                "  pip install sqlite-vss\n"
                "Or follow instructions at: https://github.com/asg017/sqlite-vss"
            )
    
    # Register event listener for future connections
    @event.listens_for(engine, "connect")
    def load_vss(dbapi_conn, connection_record):
        load_vss_for_connection(dbapi_conn)
    
    # Load for existing connections in the pool
    with engine.connect() as conn:
        load_vss_for_connection(conn.connection.dbapi_connection)


def create_vss_tables(engine: Engine) -> None:
    """
    Create virtual tables for vector similarity search.
    
    Creates VSS virtual tables for:
    - entity_vss: For Entity embeddings
    - memory_shard_vss: For MemoryShard embeddings
    
    Raises RuntimeError if VSS tables cannot be created.
    """
    with engine.connect() as conn:
        try:
            # Create VSS table for Entity embeddings
            conn.execute(text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS entity_vss USING vss0(
                    embedding(768)
                );
            """))
            
            # Create VSS table for MemoryShard embeddings  
            conn.execute(text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_shard_vss USING vss0(
                    embedding(768)
                );
            """))
            
            conn.commit()
            logger.info("VSS virtual tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create VSS tables: {e}")
            raise RuntimeError(
                f"Failed to create VSS tables (vector search is required): {e}\n"
                "This usually means the VSS extension is not properly loaded."
            )
            raise


class VectorSearchDAO:
    """Data Access Object for vector similarity search operations."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
    
    def add_entity_embedding(self, entity_id: int, embedding: List[float]) -> None:
        """Add or update an entity embedding in the VSS index."""
        with self.engine.connect() as conn:
            # Convert embedding to JSON string
            embedding_json = json.dumps(embedding)
            
            # Insert into VSS table
            conn.execute(text("""
                INSERT OR REPLACE INTO entity_vss (rowid, embedding)
                VALUES (:id, :embedding)
            """), {"id": entity_id, "embedding": embedding_json})
            conn.commit()
    
    def add_memory_embedding(self, memory_id: int, embedding: List[float]) -> None:
        """Add or update a memory shard embedding in the VSS index."""
        with self.engine.connect() as conn:
            embedding_json = json.dumps(embedding)
            
            conn.execute(text("""
                INSERT OR REPLACE INTO memory_shard_vss (rowid, embedding)
                VALUES (:id, :embedding)
            """), {"id": memory_id, "embedding": embedding_json})
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
        with self.engine.connect() as conn:
            query_json = json.dumps(query_embedding)
            
            result = conn.execute(text("""
                SELECT rowid, distance
                FROM entity_vss
                WHERE vss_search(embedding, vss_search_params(:query, :limit))
                ORDER BY distance
            """), {"query": query_json, "limit": limit})
            
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
        with self.engine.connect() as conn:
            query_json = json.dumps(query_embedding)
            
            if agent_id:
                # Filter by agent_id by joining with memory_shards table
                result = conn.execute(text("""
                    SELECT v.rowid, v.distance
                    FROM memory_shard_vss v
                    JOIN memory_shards m ON v.rowid = m.id
                    WHERE vss_search(v.embedding, vss_search_params(:query, :limit))
                    AND m.agent_id = :agent_id
                    ORDER BY v.distance
                """), {"query": query_json, "limit": limit, "agent_id": agent_id})
            else:
                result = conn.execute(text("""
                    SELECT rowid, distance
                    FROM memory_shard_vss
                    WHERE vss_search(embedding, vss_search_params(:query, :limit))
                    ORDER BY distance
                """), {"query": query_json, "limit": limit})
            
            return [(row[0], row[1]) for row in result]
    
    def bulk_add_entity_embeddings(self, embeddings: List[Tuple[int, List[float]]]) -> None:
        """Bulk add entity embeddings for efficiency."""
        with self.engine.connect() as conn:
            for entity_id, embedding in embeddings:
                embedding_json = json.dumps(embedding)
                conn.execute(text("""
                    INSERT OR REPLACE INTO entity_vss (rowid, embedding)
                    VALUES (:id, :embedding)
                """), {"id": entity_id, "embedding": embedding_json})
            conn.commit()
    
    def remove_entity_embedding(self, entity_id: int) -> None:
        """Remove an entity from the VSS index."""
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM entity_vss WHERE rowid = :id"), {"id": entity_id})
            conn.commit()
    
    def remove_memory_embedding(self, memory_id: int) -> None:
        """Remove a memory shard from the VSS index."""
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM memory_shard_vss WHERE rowid = :id"), {"id": memory_id})
            conn.commit()


# Example usage and integration with StorageRuntime
"""
from kairix_core.runtime.storage import StorageRuntime
from kairix_core.runtime.vector_storage import enable_sqlite_vss, create_vss_tables, VectorSearchDAO

# In StorageRuntime.__init__ or similar:
storage = StorageRuntime()

# Enable VSS extension
enable_sqlite_vss(storage.engine)

# Create VSS tables
create_vss_tables(storage.engine)

# Create vector search DAO
vector_dao = VectorSearchDAO(storage.engine)

# When creating an entity with embedding:
with storage.session() as session:
    entity_dao = storage.get_dao(Entity, session)
    entity = entity_dao.create(
        name="John Doe",
        embedding=[0.1] * 128,
        # ... other fields
    )
    session.flush()  # Get the ID
    
    # Add to VSS index
    vector_dao.add_entity_embedding(entity.id, entity.embedding)

# Search for similar entities:
query_embedding = [0.2] * 128
similar_entities = vector_dao.search_similar_entities(query_embedding, limit=5)

# Get the actual entities:
with storage.session() as session:
    entity_dao = storage.get_dao(Entity, session)
    for entity_id, distance in similar_entities:
        entity = entity_dao.get_by_id(entity_id)
        print(f"Entity: {entity.name}, Distance: {distance}")
"""