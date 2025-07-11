"""
Simple vector storage without FAISS/VSS - just pure SQL and Python
"""
from typing import List, Tuple, Optional
import json
import numpy as np
from sqlalchemy import text
from sqlalchemy.engine import Engine
from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger

class SimpleVectorDAO:
    """Simple vector search without VSS/FAISS dependency"""
    
    def __init__(self, engine: Engine):
        self.engine = engine
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    
    def search_similar_memories(self, query_embedding: List[float], limit: int = 10, 
                              agent_id: Optional[int] = None) -> List[Tuple[int, float]]:
        """
        Simple brute-force vector search without VSS
        """
        if limit <= 0:
            logger.warning(f"Invalid limit {limit}, using 5")
            limit = 5
            
        with self.engine.connect() as conn:
            # Get all memory embeddings
            if agent_id:
                result = conn.execute(text("""
                    SELECT m.id, m.embedding 
                    FROM memory_shards m
                    WHERE m.embedding IS NOT NULL
                    AND m.agent_id = :agent_id
                """), {"agent_id": agent_id})
            else:
                result = conn.execute(text("""
                    SELECT id, embedding 
                    FROM memory_shards
                    WHERE embedding IS NOT NULL
                """))
            
            # Calculate similarities
            similarities = []
            for row in result:
                memory_id = row[0]
                embedding_json = row[1]
                if embedding_json:
                    try:
                        embedding = json.loads(embedding_json)
                        similarity = self.cosine_similarity(query_embedding, embedding)
                        # Convert to distance (1 - similarity)
                        distance = 1.0 - similarity
                        similarities.append((memory_id, distance))
                    except Exception as e:
                        logger.error(f"Error processing embedding for memory {memory_id}: {e}")
            
            # Sort by distance and return top k
            similarities.sort(key=lambda x: x[1])
            return similarities[:limit]
    
    def search_similar_entities(self, query_embedding: List[float], limit: int = 10) -> List[Tuple[int, float]]:
        """Simple entity search"""
        if limit <= 0:
            limit = 5
            
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, embedding 
                FROM entities
                WHERE embedding IS NOT NULL
            """))
            
            similarities = []
            for row in result:
                entity_id = row[0]
                embedding_json = row[1]
                if embedding_json:
                    try:
                        embedding = json.loads(embedding_json)
                        similarity = self.cosine_similarity(query_embedding, embedding)
                        distance = 1.0 - similarity
                        similarities.append((entity_id, distance))
                    except Exception as e:
                        logger.error(f"Error processing embedding for entity {entity_id}: {e}")
            
            similarities.sort(key=lambda x: x[1])
            return similarities[:limit]
    
    def add_memory_embedding(self, memory_id: int, embedding: List[float]) -> None:
        """Store embedding as JSON in the memory_shards table"""
        with self.engine.connect() as conn:
            embedding_json = json.dumps(embedding)
            conn.execute(text("""
                UPDATE memory_shards 
                SET embedding = :embedding
                WHERE id = :id
            """), {"id": memory_id, "embedding": embedding_json})
            conn.commit()
    
    def add_entity_embedding(self, entity_id: int, embedding: List[float]) -> None:
        """Store embedding as JSON in the entities table"""
        with self.engine.connect() as conn:
            embedding_json = json.dumps(embedding)
            conn.execute(text("""
                UPDATE entities 
                SET embedding = :embedding
                WHERE id = :id
            """), {"id": entity_id, "embedding": embedding_json})
            conn.commit()