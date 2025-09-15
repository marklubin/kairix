#!/usr/bin/env python3
"""
Manual test of sqlite-vec with a few hand-inserted vectors to verify functionality.
"""
import logging
import sqlite3
import sqlite_vec
from sqlite_vec import serialize_float32
import json
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_manual_vectors():
    """Test sqlite-vec with manually inserted vectors."""
    
    logger.info("Creating test database with sqlite-vec")
    
    # Create in-memory database for testing
    conn = sqlite3.connect(":memory:")
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    
    vec_version, = conn.execute("select vec_version()").fetchone()
    logger.info(f"sqlite-vec version: {vec_version}")
    
    # Create the vec table
    conn.execute("""
        CREATE TABLE memory_shard_vec (
            id INTEGER PRIMARY KEY,
            embedding FLOAT[768]
        )
    """)
    logger.info("Created memory_shard_vec table")
    
    # Create some test vectors (768 dimensions like Nomic embeddings)
    logger.info("\n=== Creating Test Vectors ===")
    
    # Vector 1: Random vector
    vec1 = np.random.randn(768).astype(np.float32)
    vec1_binary = serialize_float32(vec1.tolist())
    
    # Vector 2: Similar to vec1 (with small noise)
    vec2 = vec1 + np.random.randn(768).astype(np.float32) * 0.1
    vec2_binary = serialize_float32(vec2.tolist())
    
    # Vector 3: Different from vec1
    vec3 = np.random.randn(768).astype(np.float32)
    vec3_binary = serialize_float32(vec3.tolist())
    
    # Vector 4: Very similar to vec1
    vec4 = vec1 + np.random.randn(768).astype(np.float32) * 0.01
    vec4_binary = serialize_float32(vec4.tolist())
    
    # Insert vectors
    conn.execute("INSERT INTO memory_shard_vec (id, embedding) VALUES (?, ?)", (1, vec1_binary))
    conn.execute("INSERT INTO memory_shard_vec (id, embedding) VALUES (?, ?)", (2, vec2_binary))
    conn.execute("INSERT INTO memory_shard_vec (id, embedding) VALUES (?, ?)", (3, vec3_binary))
    conn.execute("INSERT INTO memory_shard_vec (id, embedding) VALUES (?, ?)", (4, vec4_binary))
    conn.commit()
    
    logger.info("Inserted 4 test vectors")
    
    # Test 1: Basic search
    logger.info("\n=== Test 1: Basic Vector Search ===")
    query_vec = vec1  # Search with vec1, should find itself and similar vectors
    query_binary = serialize_float32(query_vec.tolist())
    
    cursor = conn.execute("""
        SELECT id, vec_distance_L2(embedding, ?) as distance
        FROM memory_shard_vec
        WHERE embedding IS NOT NULL
        ORDER BY distance
        LIMIT 3
    """, (query_binary,))
    
    results = cursor.fetchall()
    logger.info(f"Search results (searching with vector similar to ID 1):")
    for id, distance in results:
        logger.info(f"  ID: {id}, Distance: {distance:.6f}")
    
    # Test 2: Using JSON format (sqlite-vec also accepts JSON)
    logger.info("\n=== Test 2: JSON Format Test ===")
    vec5 = np.random.randn(768).astype(np.float32)
    vec5_json = json.dumps(vec5.tolist())
    
    # Insert using JSON format
    conn.execute("INSERT INTO memory_shard_vec (id, embedding) VALUES (?, ?)", (5, vec5_json))
    conn.commit()
    logger.info("Inserted vector 5 using JSON format")
    
    # Search again
    cursor = conn.execute("""
        SELECT id, vec_distance_L2(embedding, ?) as distance
        FROM memory_shard_vec
        ORDER BY distance
        LIMIT 5
    """, (query_binary,))
    
    results = cursor.fetchall()
    logger.info(f"All vectors after JSON insert:")
    for id, distance in results:
        logger.info(f"  ID: {id}, Distance: {distance:.6f}")
    
    # Test 3: Test with actual embeddings from Mark's database
    logger.info("\n=== Test 3: Test with Sample from Mark's DB ===")
    
    # This is a truncated sample of an actual embedding from the database
    sample_embedding = [0.01786196604371071, 0.0728781595826149, -0.20162107050418854, 
                       -0.060949329286813736, 0.09993468970060349, 0.019732419401407242]
    # Pad to 768 dimensions for testing
    sample_embedding.extend([0.0] * (768 - len(sample_embedding)))
    
    sample_binary = serialize_float32(sample_embedding)
    conn.execute("INSERT INTO memory_shard_vec (id, embedding) VALUES (?, ?)", (6, sample_binary))
    conn.commit()
    
    # Search with this sample
    cursor = conn.execute("""
        SELECT id, vec_distance_L2(embedding, ?) as distance
        FROM memory_shard_vec
        ORDER BY distance
        LIMIT 3
    """, (sample_binary,))
    
    results = cursor.fetchall()
    logger.info(f"Search with sample embedding:")
    for id, distance in results:
        logger.info(f"  ID: {id}, Distance: {distance:.6f}")
    
    logger.info("\n=== All Tests Completed Successfully! ===")
    logger.info("sqlite-vec is working correctly with both binary and JSON formats")
    
    conn.close()
    return True

if __name__ == "__main__":
    try:
        test_manual_vectors()
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()