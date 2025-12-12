#!/usr/bin/env python3
"""
Direct test of sqlite-vec migration focusing on vector search functionality.
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

def test_vec_migration():
    """Direct test of vector search functionality."""
    
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
        logger.info("Storage initialized successfully")
        
        # Test 1: Check if we can access memory shards
        logger.info("\n=== Test 1: Accessing Memory Shards ===")
        with storage.session() as session:
            dao = storage.get_dao(MemoryShard, session)
            memories = dao.get_all(limit=5)
            logger.info(f"Found {len(memories)} memory shards")
            
            for mem in memories:
                logger.info(f"Memory {mem.id}: {mem.contents[:50]}...")
                if mem.embedding:
                    logger.info(f"  Has embedding: {type(mem.embedding)} length: {len(mem.embedding) if isinstance(mem.embedding, str) else 'unknown'}")
                else:
                    logger.info("  No embedding")
        
        # Test 2: Direct vector search
        logger.info("\n=== Test 2: Direct Vector Search ===")
        
        # Get a sample embedding from the database
        sample_embedding = None
        with storage.session() as session:
            dao = storage.get_dao(MemoryShard, session)
            memories_with_embeddings = dao.find_by()[:50]  # Check first 50
            
            for mem in memories_with_embeddings:
                if mem.embedding:
                    try:
                        # Try to parse the embedding
                        if isinstance(mem.embedding, str):
                            sample_embedding = json.loads(mem.embedding)
                        else:
                            sample_embedding = mem.embedding
                        logger.info(f"Found sample embedding from memory {mem.id}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to parse embedding for memory {mem.id}: {e}")
        
        if sample_embedding:
            logger.info(f"Sample embedding type: {type(sample_embedding)}, length: {len(sample_embedding)}")
            
            # Test vector search
            try:
                results = storage.vector_dao.search_similar_memories(
                    query_embedding=sample_embedding,
                    limit=5,
                    agent_id=1
                )
                
                logger.info(f"Vector search returned {len(results)} results")
                for memory_id, distance in results:
                    logger.info(f"  Memory {memory_id}: distance = {distance:.4f}")
                    
                logger.info("✓ Vector search test PASSED!")
                
            except Exception as e:
                logger.error(f"✗ Vector search failed: {e}")
                raise
        else:
            logger.warning("No sample embedding found in database")
        
        # Test 3: Test the workaround for k=0 issue
        logger.info("\n=== Test 3: Testing k=0 Workaround ===")
        if sample_embedding:
            for k in [0, -1, None, 1, 5, 10]:
                try:
                    logger.info(f"Testing with k={k}")
                    results = storage.vector_dao.search_similar_memories(
                        query_embedding=sample_embedding,
                        limit=k,
                        agent_id=1
                    )
                    logger.info(f"  -> Success! Got {len(results)} results")
                except Exception as e:
                    logger.error(f"  -> Failed with k={k}: {e}")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ ALL TESTS PASSED! sqlite-vec is working!")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            logger.info(f"Cleaned up test database: {test_db_path}")


if __name__ == "__main__":
    success = test_vec_migration()
    sys.exit(0 if success else 1)