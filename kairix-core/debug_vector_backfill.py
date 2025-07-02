from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.types.neo4j import MemoryShard
from kairix_core.runtime.neo4j import Neo4jRuntime
from kairix_core.runtime.nlp import NLPRuntime
from neomodel import db

neo4j = Neo4jRuntime()
nlp = NLPRuntime()
logger = LoggingRuntime().logger


def debug_vector_issue():
    """Debug why vector_address isn't being saved"""
    neo4j.install()
    
    # First, let's check if the vector index exists
    logger.info("Checking for vector indexes...")
    query = "SHOW INDEXES"
    results, meta = db.cypher_query(query)
    
    vector_indexes = [r for r in results if 'vector' in str(r).lower()]
    logger.info(f"Vector indexes found: {vector_indexes}")
    
    # Get a single shard to test
    shard = MemoryShard.nodes.first()
    if not shard:
        logger.error("No shards found!")
        return
    
    logger.info(f"Testing with shard: {shard.uid}")
    logger.info(f"Original contents preview: {shard.shard_contents[:50]}...")
    
    # Method 1: Direct property update (your current approach)
    logger.info("\n=== Method 1: Direct property update ===")
    contents = shard.shard_contents[9:] if len(shard.shard_contents) > 9 else shard.shard_contents
    embedding = nlp.semantic_embedder.encode(contents).tolist()
    logger.info(f"Embedding shape: {len(embedding)} dimensions")
    logger.info(f"First few values: {embedding[:5]}")
    
    shard.vector_address = embedding
    shard.save()
    
    # Verify it was saved
    shard.refresh()
    logger.info(f"After save - vector_address exists: {hasattr(shard, 'vector_address')}")
    logger.info(f"After save - vector_address value: {shard.vector_address[:5] if shard.vector_address else 'None'}")
    
    # Method 2: Using raw Cypher query
    logger.info("\n=== Method 2: Raw Cypher update ===")
    query = """
    MATCH (s:MemoryShard {uid: $uid})
    SET s.vector_address = $embedding
    RETURN s.vector_address as vector
    """
    results, meta = db.cypher_query(query, {'uid': shard.uid, 'embedding': embedding})
    logger.info(f"Cypher update result: {results[0][0][:5] if results else 'No result'}")
    
    # Method 3: Check the actual node properties in Neo4j
    logger.info("\n=== Method 3: Check all node properties ===")
    query = """
    MATCH (s:MemoryShard {uid: $uid})
    RETURN properties(s) as props
    """
    results, meta = db.cypher_query(query, {'uid': shard.uid})
    if results:
        props = results[0][0]
        logger.info(f"All properties on node: {list(props.keys())}")
        if 'vector_address' in props:
            logger.info(f"vector_address found! Length: {len(props['vector_address'])}")
        else:
            logger.info("vector_address NOT found in properties!")


def backfill_with_cypher():
    """Alternative backfill using direct Cypher queries"""
    neo4j.install()
    
    # First ensure the index exists
    logger.info("Creating vector index if not exists...")
    try:
        query = """
        CREATE VECTOR INDEX vector_index_MemoryShard_vector_address IF NOT EXISTS
        FOR (n:MemoryShard) 
        ON (n.vector_address)
        OPTIONS {
          indexConfig: {
            `vector.dimensions`: 128,
            `vector.similarity_function`: 'cosine'
          }
        }
        """
        db.cypher_query(query)
    except Exception as e:
        logger.warning(f"Index creation failed (may already exist): {e}")
    
    # Get all shards
    count_query = "MATCH (s:MemoryShard) RETURN count(s) as count"
    results, _ = db.cypher_query(count_query)
    total = results[0][0]
    logger.info(f"Found {total} shards to process")
    
    # Process in batches
    batch_size = 100
    for offset in range(0, total, batch_size):
        logger.info(f"Processing batch {offset}-{offset+batch_size}")
        
        query = """
        MATCH (s:MemoryShard)
        WITH s SKIP $skip LIMIT $limit
        RETURN s.uid as uid, s.shard_contents as contents
        """
        results, _ = db.cypher_query(query, {'skip': offset, 'limit': batch_size})
        
        for uid, contents in results:
            if contents and len(contents) > 9:
                clean_contents = contents[9:]
                embedding = nlp.semantic_embedder.encode(clean_contents).tolist()
                
                update_query = """
                MATCH (s:MemoryShard {uid: $uid})
                SET s.shard_contents = $contents,
                    s.vector_address = $embedding
                RETURN s.uid
                """
                db.cypher_query(update_query, {
                    'uid': uid,
                    'contents': clean_contents,
                    'embedding': embedding
                })
        
        logger.info(f"Completed batch {offset}-{offset+batch_size}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "backfill":
        logger.info("Running backfill with Cypher...")
        backfill_with_cypher()
    else:
        logger.info("Running debug...")
        debug_vector_issue()