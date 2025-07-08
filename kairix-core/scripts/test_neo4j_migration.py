#!/usr/bin/env python3
"""Test Neo4j connection and migration debugging."""
import sys
import traceback
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_neo4j_connection(neo4j_url: str):
    """Test basic Neo4j connection."""
    print(f"Testing Neo4j connection to: {neo4j_url}")
    
    try:
        from neomodel import config as neomodel_config, db
        
        # Set up connection
        neomodel_config.DATABASE_URL = neo4j_url
        db.set_connection(neo4j_url)
        
        # Test basic query
        results, meta = db.cypher_query("RETURN 1 as test")
        print("✓ Neo4j connection successful!")
        print(f"  Test query result: {results}")
        
        # Check for nodes
        results, meta = db.cypher_query("MATCH (n) RETURN count(n) as node_count LIMIT 1")
        node_count = results[0][0] if results else 0
        print(f"  Total nodes in database: {node_count}")
        
        # Check for specific node types
        node_types = ['Agent', 'Concept', 'SourceDocument', 'Summary', 'MemoryShard', 'ConversationPair']
        for node_type in node_types:
            results, meta = db.cypher_query(f"MATCH (n:{node_type}) RETURN count(n) as count")
            count = results[0][0] if results else 0
            print(f"  {node_type}: {count} nodes")
            
        return True
        
    except Exception as e:
        print(f"✗ Neo4j connection failed: {e}")
        traceback.print_exc()
        return False


def test_migration_step_by_step(neo4j_url: str, sqlite_path: str = "kairix.db"):
    """Test migration step by step to identify failures."""
    print(f"\nTesting migration from {neo4j_url} to {sqlite_path}")
    
    try:
        from kairix_core.database.neo4j_to_sqlite import Neo4jToSQLiteConverter
        from kairix_core.runtime.storage import StorageRuntime
        
        # Create converter with explicit SQLite path
        storage = StorageRuntime(db_path=sqlite_path)
        converter = Neo4jToSQLiteConverter(neo4j_url, storage)
        
        # Test each conversion step individually
        steps = [
            ("Agents", converter._convert_agents),
            ("Concepts to Entities", converter._convert_concepts_to_entities),
            ("Semantic Linkages", converter._convert_semantic_linkages),
            ("Source Documents", converter._convert_source_documents),
            ("Summaries", converter._convert_summaries),
            ("Memory Shards", converter._convert_memory_shards),
            ("Conversation History", converter._convert_conversation_history),
        ]
        
        for step_name, step_func in steps:
            try:
                print(f"\n  Testing {step_name}...")
                step_func()
                print(f"  ✓ {step_name} completed")
            except Exception as e:
                print(f"  ✗ {step_name} failed: {e}")
                traceback.print_exc()
                # Continue to next step to see all failures
                
    except Exception as e:
        print(f"✗ Migration setup failed: {e}")
        traceback.print_exc()


def check_dependencies():
    """Check if required dependencies are installed."""
    print("Checking dependencies...")
    
    deps = {
        'neomodel': 'Neo4j ORM',
        'sentence_transformers': 'Embeddings',
        'sqlalchemy': 'SQLite ORM',
    }
    
    missing = []
    for module, desc in deps.items():
        try:
            __import__(module)
            print(f"  ✓ {desc} ({module})")
        except ImportError:
            print(f"  ✗ {desc} ({module}) - NOT INSTALLED")
            missing.append(module)
            
    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Install with: uv add " + " ".join(missing))
        return False
    return True


def main():
    """Main test function."""
    if len(sys.argv) < 2:
        print("Usage: python test_neo4j_migration.py <neo4j_url> [sqlite_path]")
        print("Example: python test_neo4j_migration.py bolt://neo4j:password@localhost:7687")
        return
        
    neo4j_url = sys.argv[1]
    sqlite_path = sys.argv[2] if len(sys.argv) > 2 else "kairix.db"
    
    # Check dependencies first
    if not check_dependencies():
        return
        
    # Test connection
    if test_neo4j_connection(neo4j_url):
        # Test migration
        test_migration_step_by_step(neo4j_url, sqlite_path)
    else:
        print("\nSkipping migration test due to connection failure")


if __name__ == "__main__":
    main()