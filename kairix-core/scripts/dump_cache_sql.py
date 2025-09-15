#!/usr/bin/env python3
"""Generate SQL from cache database directly."""

import sqlite3
import json
from pathlib import Path

# Connect to the cache database
cache_db = Path(".cache/000/cache.db")
if not cache_db.exists():
    cache_db = Path(".cache/index/summarization_errors/cache.db")

if not cache_db.exists():
    print("-- No cache database found")
    exit(1)

conn = sqlite3.connect(f"file:{str(cache_db)}?mode=ro", uri=True)
cursor = conn.cursor()

# Get all key-value pairs from the cache
try:
    cursor.execute("SELECT key, value FROM Cache")
    entries = cursor.fetchall()
    
    print(f"-- Found {len(entries)} cached entries")
    print("-- SQL Insert statements for memory_shards table\n")
    
    # Extract unique agents
    agents = set()
    for key, value in entries:
        if key.startswith("incremental-reflection-v1."):
            parts = key.split(".")
            if len(parts) >= 3:
                agents.add(parts[1])
    
    # Generate agent inserts
    print("-- Insert agents if they don't exist")
    for agent_name in agents:
        print(f"INSERT OR IGNORE INTO agents (name, created_at, updated_at) VALUES ('{agent_name}', datetime('now'), datetime('now'));")
    
    print("\n-- Insert memory shards")
    
    # Generate memory shard inserts
    for key, value in entries:
        if key.startswith("incremental-reflection-v1."):
            parts = key.split(".")
            if len(parts) >= 3:
                agent_name = parts[1]
                
                # The value might be pickled or raw text
                try:
                    # Try to decode as text
                    if isinstance(value, bytes):
                        summary_text = value.decode('utf-8')
                    else:
                        summary_text = str(value)
                    
                    # Escape quotes
                    escaped_summary = summary_text.replace("'", "''")
                    
                    # Generate placeholder embedding
                    embedding = [0.0] * 768
                    embedding_json = json.dumps(embedding)
                    
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
                    print(f"-- Error processing entry {key}: {e}")
    
except sqlite3.Error as e:
    print(f"-- Error reading cache database: {e}")
    # Try to list tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"-- Available tables: {tables}")

conn.close()