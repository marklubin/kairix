#!/usr/bin/env python3
"""Extract summarization errors from CacheRuntime and generate SQL."""

import sys
from pathlib import Path
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.kairix_core.runtime.cache import CacheRuntime

def main():
    """Extract cache entries and generate SQL."""
    # Get the summarization_errors cache
    cache = CacheRuntime().summarization_errors
    
    print(f"-- Found {len(cache)} cached summaries")
    print("-- SQL Insert statements for memory_shards table\n")
    
    # Extract unique agents
    agents = set()
    for key in cache.keys():
        parts = key.split(".")
        if len(parts) >= 3:
            agents.add(parts[1])
    
    # Generate agent inserts
    print("-- Insert agents if they don't exist")
    for agent_name in agents:
        print(f"INSERT OR IGNORE INTO agents (name, created_at, updated_at) VALUES ('{agent_name}', datetime('now'), datetime('now'));")
    
    print("\n-- Insert memory shards")
    
    # Process each cached summary
    for key in cache.keys():
        try:
            summary_text = cache[key]
            
            # Parse agent name from key format: "incremental-reflection-v1.{agent_name}.{timestamp}"
            parts = key.split(".")
            if len(parts) < 3:
                print(f"-- Warning: Invalid key format: {key}")
                continue
                
            agent_name = parts[1]
            
            # Escape single quotes in summary text
            escaped_summary = summary_text.replace("'", "''")
            
            # Generate a placeholder embedding (768 dimensions of zeros)
            embedding = [0.0] * 768
            embedding_json = json.dumps(embedding)
            
            # Generate SQL insert
            print(f"""
INSERT INTO memory_shards (
    contents,
    embedding_type,
    embedding,
    agent_id,
    created_at,
    updated_at
) VALUES (
    '{escaped_summary}',
    'kairix-default-768',
    '{embedding_json}',
    (SELECT id FROM agents WHERE name = '{agent_name}'),
    datetime('now'),
    datetime('now')
);""")
            
        except Exception as e:
            print(f"-- Error processing key {key}: {str(e)}")
    
    print("\n-- End of SQL statements")


if __name__ == "__main__":
    main()