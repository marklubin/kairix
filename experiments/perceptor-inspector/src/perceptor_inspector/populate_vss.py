"""Populate VSS index from existing embeddings."""
import os
os.environ['KAIRIX_LOG_LEVEL'] = 'INFO'
os.environ['KAIRIX_USER_NAME'] = 'mark'

from kairix_core.runtime.storage import StorageRuntime
from kairix_core.types.db import MemoryShard
from sqlalchemy import text

storage = StorageRuntime(db_path="../.sqlite/mark.db")

with storage.session() as session:
    # Get all shards with embeddings
    shards = session.query(MemoryShard).filter(MemoryShard.embedding is not None).all()
    print(f"Found {len(shards)} shards with embeddings")
    
    # Populate VSS
    with storage.engine.connect() as conn:
        populated = 0
        for shard in shards:
            if shard.embedding and len(shard.embedding) == 768:
                try:
                    # Insert into VSS
                    embedding_str = '[' + ','.join(str(x) for x in shard.embedding) + ']'
                    conn.execute(text(
                        "INSERT INTO memory_shard_vss (rowid, embedding) VALUES (:rowid, :embedding)"
                    ), {"rowid": shard.id, "embedding": embedding_str})
                    populated += 1
                    if populated % 100 == 0:
                        print(f"Populated {populated} entries...")
                except Exception as e:
                    print(f"Error on shard {shard.id}: {e}")
        
        conn.commit()
        print(f"Successfully populated {populated} VSS entries")