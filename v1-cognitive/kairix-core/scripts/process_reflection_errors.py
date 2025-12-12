#!/usr/bin/env python3
"""
Backfill script to process cached incremental reflection summaries 
and persist them to SQLite database.
"""

import os
import sys
from pathlib import Path
from doppler_client import inject_doppler_env
from diskcache import FanoutCache
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.kairix_core.data_access.agent_dao import AgentDAO
from src.kairix_core.data_access.memory_dao import MemoryDAO
from src.kairix_core.integrations.litellm import get_embedder


def main():
    """Process all cached reflection errors and persist them to SQLite."""
    # Try to inject Doppler environment variables, but continue if it fails
    try:
        inject_doppler_env()
    except Exception as e:
        print(f"Warning: Could not inject Doppler env: {e}")
    
    # Initialize cache
    cache_path = Path(".cache")
    cache = FanoutCache(cache_path, name="summarization_errors", timeout=1)
    
    # Get database URL from environment or use default
    db_url = os.environ.get("KAIRIX_SQLALCHEMY_URL", f"sqlite:///{Path.cwd() / '.kairix' / 'k.db'}")
    print(f"Using database: {db_url}")
    
    # Initialize database
    engine = create_engine(db_url)
    
    # Initialize DAOs
    agent_dao = AgentDAO(engine)
    memory_dao = MemoryDAO(engine)
    
    # Initialize embedder
    embedder = get_embedder()
    
    print(f"Found {len(cache)} cached summaries to process")
    
    processed = 0
    errors = 0
    
    # Process each cached summary
    for key in list(cache.keys()):
        try:
            summary_text = cache[key]
            
            # Parse agent name from key format: "incremental-reflection-v1.{agent_name}.{timestamp}"
            parts = key.split(".")
            if len(parts) < 3:
                print(f"Warning: Invalid key format: {key}")
                continue
                
            agent_name = parts[1]
            
            print(f"Processing summary for agent: {agent_name}")
            
            # Find or create agent
            with Session(engine):
                db_agent = agent_dao.find_one_by(name=agent_name)
                if not db_agent:
                    print(f"Creating new agent: {agent_name}")
                    db_agent = agent_dao.create(name=agent_name)
            
            # Generate embedding
            embedding = embedder.embed_text(summary_text)
            
            # Create memory shard
            with Session(engine):
                memory_dao.create(
                    contents=summary_text,
                    embedding_type="kairix-default-768",
                    embedding=embedding,
                    agent_id=db_agent.id
                )
            
            # Remove from cache after successful processing
            del cache[key]
            processed += 1
            print(f"Successfully processed summary for {agent_name}")
            
        except Exception as e:
            print(f"Error processing key {key}: {str(e)}")
            errors += 1
    
    print("\nBackfill complete:")
    print(f"  Processed: {processed}")
    print(f"  Errors: {errors}")
    print(f"  Remaining in cache: {len(cache)}")


if __name__ == "__main__":
    main()