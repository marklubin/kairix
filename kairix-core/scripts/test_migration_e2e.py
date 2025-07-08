#!/usr/bin/env python3
"""End-to-end test for Neo4j to SQLite migration with sample data."""
import sys
import os
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def extract_neo4j_samples(neo4j_url: str):
    """Extract a small sample of data from Neo4j for testing."""
    print("Extracting sample data from Neo4j...")
    
    try:
        from neomodel import config as neomodel_config, db
        
        # Connect to Neo4j
        neomodel_config.DATABASE_URL = neo4j_url
        db.set_connection(neo4j_url)
        
        samples = {}
        
        # Get sample agents (limit 2)
        query = "MATCH (a:Agent) RETURN a.name as name LIMIT 2"
        results, _ = db.cypher_query(query)
        samples['agents'] = [{'name': row[0]} for row in results if row[0]]
        print(f"  Found {len(samples['agents'])} agents")
        
        # Get sample concepts (limit 3 of different types)
        query = """
        MATCH (c:Concept) 
        WITH c.type as type, collect(c)[0..2] as concepts
        UNWIND concepts as concept
        RETURN concept.semantic_id as semantic_id, 
               concept.name as name, 
               concept.type as type,
               concept.created_at as created_at
        LIMIT 5
        """
        results, _ = db.cypher_query(query)
        samples['concepts'] = []
        for row in results:
            if row[0]:  # Skip if semantic_id is None
                samples['concepts'].append({
                    'semantic_id': row[0],
                    'name': row[1] or row[0],  # Use semantic_id if name is None
                    'type': row[2] or 'unknown',
                    'created_at': row[3] or datetime.utcnow()
                })
        print(f"  Found {len(samples['concepts'])} concepts")
        
        # Get sample memory shards (limit 3)
        query = """
        MATCH (m:MemoryShard) 
        OPTIONAL MATCH (m)-[:AGENT]-(a:Agent)
        RETURN m.uid as uid, 
               m.shard_contents as contents,
               a.name as agent_name,
               m.created_at as created_at
        LIMIT 3
        """
        results, _ = db.cypher_query(query)
        samples['memory_shards'] = []
        for row in results:
            if row[0] and row[1]:  # Skip if uid or contents is None
                samples['memory_shards'].append({
                    'uid': row[0],
                    'contents': row[1],
                    'agent_name': row[2] or 'default',
                    'created_at': row[3] or datetime.utcnow()
                })
        print(f"  Found {len(samples['memory_shards'])} memory shards")
        
        # Get sample semantic linkages (limit 3)
        query = """
        MATCH (s:Concept)-[r:semantic_linkage]->(t:Concept)
        RETURN s.semantic_id as source_id,
               t.semantic_id as target_id,
               r.linkage_type as linkage_type,
               r.weight as weight
        LIMIT 3
        """
        results, _ = db.cypher_query(query)
        samples['linkages'] = []
        for row in results:
            if row[0] and row[1]:  # Skip if source or target is None
                samples['linkages'].append({
                    'source_id': row[0],
                    'target_id': row[1],
                    'linkage_type': row[2] or 'related_to',
                    'weight': row[3] or 1.0
                })
        print(f"  Found {len(samples['linkages'])} linkages")
        
        # Get sample source documents (limit 2)
        query = """
        MATCH (d:SourceDocument)
        RETURN d.uid as uid,
               d.content as content,
               d.source_type as source_type,
               d.source_label as source_label
        LIMIT 2
        """
        results, _ = db.cypher_query(query)
        samples['source_documents'] = []
        for row in results:
            if row[0]:  # Skip if uid is None
                samples['source_documents'].append({
                    'uid': row[0],
                    'content': row[1] or 'No content',
                    'source_type': row[2] or 'unknown',
                    'source_label': row[3] or 'unknown'
                })
        print(f"  Found {len(samples['source_documents'])} source documents")
        
        return samples
        
    except Exception as e:
        print(f"Error extracting samples: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_migration_test(neo4j_url: str, samples: dict):
    """Run the migration and verify results."""
    print("\nRunning migration test...")
    
    # Create temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        test_db_path = tmp.name
    
    try:
        # Import and run migration
        from kairix_core.database.neo4j_to_sqlite import Neo4jToSQLiteConverter
        from kairix_core.runtime.storage import StorageRuntime
        
        # Create storage with test database
        storage = StorageRuntime(db_path=test_db_path)
        
        # Run migration
        converter = Neo4jToSQLiteConverter(neo4j_url, storage)
        converter.convert_all()
        
        print(f"\nMigration completed. Verifying data in {test_db_path}...")
        
        # Verify migrated data
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check agents
        cursor.execute("SELECT COUNT(*) as count FROM agents")
        agent_count = cursor.fetchone()['count']
        print(f"\n✓ Agents table: {agent_count} records")
        
        cursor.execute("SELECT name FROM agents")
        for row in cursor.fetchall():
            print(f"  - {row['name']}")
        
        # Check entities (converted from concepts)
        cursor.execute("SELECT COUNT(*) as count FROM entities")
        entity_count = cursor.fetchone()['count']
        print(f"\n✓ Entities table: {entity_count} records")
        
        cursor.execute("SELECT semantic_id, name, entity_class FROM entities LIMIT 5")
        for row in cursor.fetchall():
            print(f"  - {row['semantic_id']} ({row['entity_class']}): {row['name']}")
        
        # Check memory shards
        cursor.execute("SELECT COUNT(*) as count FROM memory_shards")
        memory_count = cursor.fetchone()['count']
        print(f"\n✓ Memory shards table: {memory_count} records")
        
        cursor.execute("""
            SELECT m.uid, m.contents, a.name as agent_name 
            FROM memory_shards m
            JOIN agents a ON m.agent_id = a.id
            LIMIT 3
        """)
        for row in cursor.fetchall():
            content_preview = row['contents'][:50] + '...' if len(row['contents']) > 50 else row['contents']
            print(f"  - {row['uid']} (agent: {row['agent_name']}): {content_preview}")
        
        # Check semantic linkages
        cursor.execute("SELECT COUNT(*) as count FROM semantic_linkages")
        linkage_count = cursor.fetchone()['count']
        print(f"\n✓ Semantic linkages table: {linkage_count} records")
        
        cursor.execute("""
            SELECT e1.semantic_id as source, e2.semantic_id as target, sl.linkage_type
            FROM semantic_linkages sl
            JOIN entities e1 ON sl.source_id = e1.id
            JOIN entities e2 ON sl.target_id = e2.id
            LIMIT 3
        """)
        for row in cursor.fetchall():
            print(f"  - {row['source']} -> {row['target']} ({row['linkage_type']})")
        
        # Check source objects
        cursor.execute("SELECT COUNT(*) as count FROM source_objects")
        source_count = cursor.fetchone()['count']
        print(f"\n✓ Source objects table: {source_count} records")
        
        # Verify entity classes and linkage types were created
        cursor.execute("SELECT COUNT(*) as count FROM entity_class")
        class_count = cursor.fetchone()['count']
        print(f"\n✓ Entity classes: {class_count} types")
        
        cursor.execute("SELECT COUNT(*) as count FROM linkage_type")
        type_count = cursor.fetchone()['count']
        print(f"✓ Linkage types: {type_count} types")
        
        conn.close()
        
        # Summary
        print("\n" + "="*60)
        print("MIGRATION TEST SUMMARY:")
        print(f"  Agents:           {agent_count}")
        print(f"  Entities:         {entity_count}")
        print(f"  Memory Shards:    {memory_count}")
        print(f"  Linkages:         {linkage_count}")
        print(f"  Source Objects:   {source_count}")
        print("="*60)
        
        if agent_count > 0 and entity_count > 0:
            print("\n✅ Migration test PASSED!")
            return True
        else:
            print("\n❌ Migration test FAILED - no data migrated")
            return False
            
    except Exception as e:
        print(f"\n❌ Migration test FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up test database
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)
            print(f"\nCleaned up test database: {test_db_path}")


def main():
    """Main test function."""
    if len(sys.argv) < 2:
        print("Usage: python test_migration_e2e.py <neo4j_url>")
        print("Example: python test_migration_e2e.py bolt://neo4j:password@localhost:7687")
        return
    
    neo4j_url = sys.argv[1]
    
    # Extract samples
    samples = extract_neo4j_samples(neo4j_url)
    if not samples:
        print("Failed to extract sample data from Neo4j")
        return
    
    # Run migration test
    success = run_migration_test(neo4j_url, samples)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()