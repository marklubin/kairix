#!/usr/bin/env python3
"""Test migration to find the 'more values than arguments' error."""
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_migration():
    """Test the migration to find the error."""
    try:
        from kairix_core.database.neo4j_to_sqlite import Neo4jToSQLiteConverter
        from kairix_core.runtime.storage import StorageRuntime
        
        # Test database
        test_db = "../.sqlite/test_migration_error.db"
        
        # Create storage runtime
        storage = StorageRuntime(db_path=test_db)
        
        # Create converter with a test Neo4j URL
        neo4j_url = "bolt://neo4j:password@localhost:7687"
        converter = Neo4jToSQLiteConverter(neo4j_url, storage)
        
        # Try to run individual conversion steps to find the error
        print("Testing agent conversion...")
        converter._convert_agents()
        print("✓ Agents conversion successful")
        
        print("\nTesting concepts to entities conversion...")
        converter._convert_concepts_to_entities()
        print("✓ Concepts conversion successful")
        
        print("\nTesting semantic linkages conversion...")
        converter._convert_semantic_linkages()
        print("✓ Linkages conversion successful")
        
        print("\nTesting source documents conversion...")
        converter._convert_source_documents()
        print("✓ Source documents conversion successful")
        
        print("\nTesting summaries conversion...")
        converter._convert_summaries()
        print("✓ Summaries conversion successful")
        
        print("\nTesting memory shards conversion...")
        converter._convert_memory_shards()
        print("✓ Memory shards conversion successful")
        
        print("\nTesting conversation history conversion...")
        converter._convert_conversation_history()
        print("✓ Conversation history conversion successful")
        
    except Exception as e:
        print(f"\n✗ Error occurred: {type(e).__name__}: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        
        # If it's a SQL error, try to find the problematic query
        if "more values than arguments" in str(e).lower():
            print("\n⚠️  This error typically means a SQL query has more placeholders (?) than values provided")
            print("Check the SQL queries in the migration code for mismatched parameters")

if __name__ == "__main__":
    test_migration()