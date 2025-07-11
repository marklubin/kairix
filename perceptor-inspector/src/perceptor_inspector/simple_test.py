"""Simple working test of memory search."""
import os
os.environ['KAIRIX_LOG_LEVEL'] = 'INFO'
os.environ['KAIRIX_USER_NAME'] = 'mark'

from kairix_core.runtime.storage import StorageRuntime
from kairix_core.types.db import MemoryShard
from kairix_core.embedding.nomic import NomicEmbedding

# Test basic functionality
storage = StorageRuntime(db_path="../.sqlite/mark.db")
embedder = NomicEmbedding()

with storage.session() as session:
    # Get a few memory shards
    shards = session.query(MemoryShard).limit(5).all()
    print(f"Found {len(shards)} shards")
    
    for shard in shards:
        print(f"\nShard {shard.id}:")
        print(f"  Content: {shard.contents[:100]}...")
        print(f"  Has embedding: {len(shard.embedding) if shard.embedding else 0}")

# Test embedding
test_text = "weather climate temperature"
embedding = embedder.encode(test_text)
print(f"\nTest embedding shape: {embedding.shape}")

# Check VSS tables
with storage.engine.connect() as conn:
    from sqlalchemy import text
    result = conn.execute(text("SELECT COUNT(*) FROM memory_shard_vss"))
    count = result.scalar()
    print(f"\nVSS table has {count} entries")