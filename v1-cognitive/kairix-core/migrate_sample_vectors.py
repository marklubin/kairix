#!/usr/bin/env python3
"""
Migrate a sample of vectors from existing database to sqlite-vec format.
"""
import logging
import os
import sys
from pathlib import Path
import tempfile
import shutil
import json

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kairix_core.runtime.storage import StorageRuntime
from kairix_core.types.db import MemoryShard

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_sample_vectors():
    """Migrate a sample of vectors to test the new format."""
    
    # Path to mark.db
    mark_db_path = "/home/kairix/kairix/.sqlite/mark.db"
    
    if not os.path.exists(mark_db_path):
        logger.error(f"Database not found at: {mark_db_path}")
        return False
    
    # Create a test copy
    test_db_path = tempfile.mktemp(suffix='.db')
    shutil.copy2(mark_db_path, test_db_path)
    logger.info(f"Created test database copy at: {test_db_path}")
    
    try:
        # Initialize storage with test DB
        storage = StorageRuntime(db_path=test_db_path)
        logger.info("Storage initialized with sqlite-vec")
        
        # Get a few memory shards with embeddings
        logger.info("\n=== Migrating Sample Vectors ===")
        with storage.session() as session:
            dao = storage.get_dao(MemoryShard, session)
            
            # Get first 10 memories with embeddings
            memories = dao.find_by()[:50]  # Check first 50
            
            migrated_count = 0
            for memory in memories:
                if memory.embedding and migrated_count < 10:
                    try:
                        # The embedding might be stored as JSON string or list
                        if isinstance(memory.embedding, str):
                            embedding_list = json.loads(memory.embedding)
                        else:
                            embedding_list = memory.embedding
                        
                        # Add to vec index
                        storage.vector_dao.add_memory_embedding(memory.id, embedding_list)
                        migrated_count += 1
                        logger.info(f"Migrated embedding for memory {memory.id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to migrate memory {memory.id}: {e}")
                
                if migrated_count >= 10:
                    break
        
        logger.info(f"\nMigrated {migrated_count} embeddings to sqlite-vec format")
        
        # Test search on migrated vectors
        logger.info("\n=== Testing Search on Migrated Vectors ===")
        
        # Get one of the migrated embeddings to use as query
        with storage.session() as session:
            dao = storage.get_dao(MemoryShard, session)
            test_memory = dao.find_by()[0]  # Get first one
            
            if test_memory.embedding:
                if isinstance(test_memory.embedding, str):
                    query_embedding = json.loads(test_memory.embedding)
                else:
                    query_embedding = test_memory.embedding
                
                # Search for similar vectors
                results = storage.vector_dao.search_similar_memories(
                    query_embedding=query_embedding,
                    limit=5,
                    agent_id=1
                )
                
                logger.info(f"Search results (found {len(results)} similar memories):")
                for memory_id, distance in results:
                    # Get the actual memory content
                    memory = dao.get_by_id(memory_id)
                    if memory:
                        logger.info(f"  Memory {memory_id} (distance: {distance:.4f}): {memory.contents[:50]}...")
                
                logger.info("\n✅ Migration and search test successful!")
                return True
            else:
                logger.error("No embedding found for test")
                return False
        
    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            logger.info(f"\nCleaned up test database: {test_db_path}")


if __name__ == "__main__":
    success = migrate_sample_vectors()
    sys.exit(0 if success else 1)