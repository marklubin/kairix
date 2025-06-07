#!/usr/bin/env python
"""Verify integration test setup is ready"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("Checking integration test prerequisites...")
print("-" * 50)

# Check Neo4j URL
neo4j_url = os.getenv("NEO4J_URL")
if neo4j_url:
    print(f"✓ NEO4J_URL is set: {neo4j_url}")
else:
    print("✗ NEO4J_URL is not set in .env file")
    print("  Please set NEO4J_URL=bolt://neo4j:password@localhost:7687")
    sys.exit(1)

# Check if Neo4j is accessible
try:
    from neomodel import config as neomodel_config, db
    neomodel_config.DATABASE_URL = neo4j_url
    
    # Try to connect
    result = db.cypher_query("RETURN 1 as test")[0]
    if result and result[0]['test'] == 1:
        print("✓ Neo4j database is accessible")
    else:
        print("✗ Neo4j database returned unexpected result")
        sys.exit(1)
except Exception as e:
    print(f"✗ Cannot connect to Neo4j database: {e}")
    print("\nPlease ensure Neo4j is running:")
    print("  docker-compose up -d neo4j")
    sys.exit(1)

print("-" * 50)
print("All prerequisites are met! You can now run:")
print("  uv run pytest tests/integration/ -v")
print("\nThe database needs to remain running during the tests.")