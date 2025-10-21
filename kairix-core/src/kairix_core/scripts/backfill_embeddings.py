"""Backfill embeddings for existing MemoryShard entries."""
from kairix_core.embedding.nomic import NomicEmbedding
from kairix_core.runtime.storage import StorageRuntime
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.types.db import MemoryShard

logger = LoggingRuntime().logger
storage = StorageRuntime(db_path="../.sqlite/mark.db")

if __name__ == "__main__":
    embedder = NomicEmbedding()
    
    with storage.session() as session:
        shards = session.query(MemoryShard).all()
        logger.info(f"Backfilling {len(shards)} shards")
        
        for i, shard in enumerate(shards):
            try:
                embedding = embedder.encode(shard.contents).tolist()[0]
                shard.embedding = embedding
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(shards)}")
            except Exception as e:
                logger.error(f"Shard {shard.id}: {e}")
        
        session.commit()