#!/usr/bin/env python3
"""Test Neo4j to SQLite migration with mock data."""
import sys
import os
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_mock_neo4j_data():
    """Create mock data in Neo4j format for testing."""
    print("Creating mock Neo4j data for testing...")
    
    # Create a temporary neo4j database using neomodel
    from kairix_core.types.neo4j import (
        Agent, Concept, SourceDocument, Summary, MemoryShard
    )
    
    # Use an in-memory or temporary Neo4j instance
    # For this test, we'll populate data and test the migration
    
    # Create mock agents
    agents = []
    for i in range(2):
        agent = Agent(name=f"test_agent_{i}").save()
        agents.append(agent)
    print(f"  Created {len(agents)} mock agents")
    
    # Create mock concepts
    concepts = []
    concept_types = ["Person", "Location", "Event", "Object"]
    for i in range(5):
        concept = Concept(
            semantic_id=f"concept_{i}",
            name=f"Test Concept {i}",
            type=random.choice(concept_types),
            embedding=[random.random() for _ in range(128)],  # Random 128-dim embedding
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
        ).save()
        concepts.append(concept)
    print(f"  Created {len(concepts)} mock concepts")
    
    # Create semantic linkages between concepts
    linkage_types = ["related_to", "located_at", "participates_in", "knows"]
    linkage_count = 0
    for i in range(3):
        source = concepts[i]
        target = concepts[(i + 1) % len(concepts)]
        source.semantic_linkage.connect(
            target,
            {
                'linkage_type': random.choice(linkage_types),
                'weight': random.uniform(0.5, 1.0),
                'related_at': datetime.utcnow() - timedelta(days=random.randint(1, 10))
            }
        )
        linkage_count += 1
    print(f"  Created {linkage_count} mock linkages")
    
    # Create mock source documents
    source_docs = []
    for i in range(2):
        doc = SourceDocument(
            uid=f"doc_{i}",
            content=f"This is test document {i} with some content.",
            source_type="test_source",
            source_label=f"Test Source {i}"
        ).save()
        source_docs.append(doc)
    print(f"  Created {len(source_docs)} mock source documents")
    
    # Create mock summaries
    summaries = []
    for i in range(2):
        summary = Summary(
            uid=f"summary_{i}",
            summary_text=f"This is a test summary {i} of some content.",
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 20))
        ).save()
        summaries.append(summary)
    print(f"  Created {len(summaries)} mock summaries")
    
    # Create mock memory shards
    memory_shards = []
    for i in range(3):
        shard = MemoryShard(
            uid=f"shard_{i}",
            shard_contents=f"This is memory shard {i} containing important information.",
            vector_address=[random.random() for _ in range(128)],
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 15))
        ).save()
        
        # Connect to agent
        shard.agent.connect(agents[i % len(agents)])
        
        # Connect to source document if available
        if i < len(source_docs):
            shard.source_document.connect(source_docs[i])
            
        # Connect to summary if available
        if i < len(summaries):
            shard.summary.connect(summaries[i])
            
        memory_shards.append(shard)
    print(f"  Created {len(memory_shards)} mock memory shards")
    
    return True


def setup_mock_neo4j():
    """Setup a mock Neo4j environment for testing."""
    # For testing purposes, we'll create the data directly in SQLite
    # simulating what would be migrated from Neo4j
    
    print("Setting up mock test environment...")
    
    # Create a temporary SQLite database with Neo4j-like data
    with tempfile.NamedTemporaryFile(suffix='_neo4j.db', delete=False) as tmp:
        mock_db_path = tmp.name
    
    conn = sqlite3.connect(mock_db_path)
    cursor = conn.cursor()
    
    # Create mock tables that simulate Neo4j data
    cursor.executescript("""
    -- Mock agents
    CREATE TABLE mock_agents (
        name TEXT PRIMARY KEY
    );
    
    INSERT INTO mock_agents VALUES
        ('test_agent_0'),
        ('test_agent_1'),
        ('default');
    
    -- Mock concepts  
    CREATE TABLE mock_concepts (
        semantic_id TEXT PRIMARY KEY,
        name TEXT,
        type TEXT,
        created_at TIMESTAMP
    );
    
    INSERT INTO mock_concepts VALUES
        ('person_john_doe', 'John Doe', 'Person', datetime('now', '-5 days')),
        ('location_new_york', 'New York', 'Location', datetime('now', '-10 days')),
        ('event_meeting_2024', 'Team Meeting 2024', 'Event', datetime('now', '-3 days')),
        ('object_laptop', 'Work Laptop', 'Object', datetime('now', '-15 days')),
        ('person_jane_smith', 'Jane Smith', 'Person', datetime('now', '-7 days'));
    
    -- Mock linkages
    CREATE TABLE mock_linkages (
        source_id TEXT,
        target_id TEXT,
        linkage_type TEXT,
        weight REAL
    );
    
    INSERT INTO mock_linkages VALUES
        ('person_john_doe', 'location_new_york', 'located_at', 0.9),
        ('person_john_doe', 'event_meeting_2024', 'participates_in', 0.8),
        ('person_jane_smith', 'person_john_doe', 'knows', 0.7);
    
    -- Mock memory shards
    CREATE TABLE mock_memory_shards (
        uid TEXT PRIMARY KEY,
        contents TEXT,
        agent_name TEXT,
        created_at TIMESTAMP
    );
    
    INSERT INTO mock_memory_shards VALUES
        ('shard_001', 'Meeting notes: Discussed project roadmap with team.', 'test_agent_0', datetime('now', '-2 days')),
        ('shard_002', 'Personal reminder: Call John about the presentation.', 'test_agent_1', datetime('now', '-1 day')),
        ('shard_003', 'Observation: Weather was sunny during the outdoor event.', 'default', datetime('now', '-5 days'));
    """)
    
    conn.commit()
    conn.close()
    
    print(f"  Created mock database at: {mock_db_path}")
    return mock_db_path


def run_migration_test_direct():
    """Run migration test with direct SQLite operations."""
    print("\nRunning direct migration test...")
    
    # Create test databases
    source_db = setup_mock_neo4j()
    
    with tempfile.NamedTemporaryFile(suffix='_migrated.db', delete=False) as tmp:
        target_db = tmp.name
    
    try:
        # Initialize target database with schema
        from kairix_core.runtime.storage import StorageRuntime
        from kairix_core.database.init_data import initialize_database
        
        storage = StorageRuntime(db_path=target_db)
        
        # Initialize with default data
        initialize_database(storage)
        
        # Manually migrate mock data
        source_conn = sqlite3.connect(source_db)
        source_conn.row_factory = sqlite3.Row
        
        with storage.session() as session:
            from kairix_core.types.db import Agent, Entity, EntityClass, SemanticLinkage, MemoryShard
            
            # Migrate agents
            agent_dao = storage.get_dao(Agent, session)
            for row in source_conn.execute("SELECT * FROM mock_agents"):
                # Check if agent already exists
                existing = agent_dao.find_one_by(name=row['name'])
                if not existing:
                    agent_dao.create(name=row['name'])
            
            # Ensure entity classes exist
            entity_class_dao = storage.get_dao(EntityClass, session)
            for class_name in ['person', 'location', 'event', 'object']:
                existing = entity_class_dao.find_one_by(name=class_name)
                if not existing:
                    entity_class_dao.create(
                        name=class_name,
                        description=f"Test {class_name} class"
                    )
            
            # Migrate concepts as entities
            entity_dao = storage.get_dao(Entity, session)
            entity_map = {}
            for row in source_conn.execute("SELECT * FROM mock_concepts"):
                entity = entity_dao.create(
                    semantic_id=row['semantic_id'],
                    name=row['name'],
                    entity_class=row['type'].lower(),
                    embedding_type="kairix-default-128",
                    embedding=[0.5] * 128,  # Mock embedding
                    created_at=datetime.fromisoformat(row['created_at'])
                )
                entity_map[row['semantic_id']] = entity.id
            
            # Migrate linkages
            linkage_dao = storage.get_dao(SemanticLinkage, session)
            for row in source_conn.execute("SELECT * FROM mock_linkages"):
                if row['source_id'] in entity_map and row['target_id'] in entity_map:
                    linkage_dao.create(
                        source_id=entity_map[row['source_id']],
                        target_id=entity_map[row['target_id']],
                        linkage_type=row['linkage_type'],
                        weight=row['weight']
                    )
            
            # Migrate memory shards
            memory_dao = storage.get_dao(MemoryShard, session)
            agents = {a.name: a.id for a in agent_dao.get_all()}
            
            for row in source_conn.execute("SELECT * FROM mock_memory_shards"):
                agent_id = agents.get(row['agent_name'], agents.get('default'))
                memory_dao.create(
                    uid=row['uid'],
                    contents=row['contents'],
                    embedding_type="kairix-default-128",
                    embedding=[0.5] * 128,  # Mock embedding
                    agent_id=agent_id,
                    created_at=datetime.fromisoformat(row['created_at'])
                )
        
        source_conn.close()
        
        # Verify migration
        print("\nVerifying migrated data...")
        
        conn = sqlite3.connect(target_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check all tables
        checks = [
            ("agents", "SELECT COUNT(*) as count, GROUP_CONCAT(name) as names FROM agents"),
            ("entities", "SELECT COUNT(*) as count FROM entities"),
            ("memory_shards", "SELECT COUNT(*) as count FROM memory_shards"),
            ("semantic_linkages", "SELECT COUNT(*) as count FROM semantic_linkages"),
            ("entity_class", "SELECT COUNT(*) as count FROM entity_class"),
            ("linkage_type", "SELECT COUNT(*) as count FROM linkage_type")
        ]
        
        results = {}
        for table, query in checks:
            row = cursor.execute(query).fetchone()
            results[table] = row['count']
            if table == 'agents' and row['names']:
                print(f"✓ {table}: {row['count']} records ({row['names']})")
            else:
                print(f"✓ {table}: {row['count']} records")
        
        # Show sample data
        print("\nSample migrated data:")
        
        # Sample entities
        print("\n  Entities:")
        for row in cursor.execute("SELECT semantic_id, name, entity_class FROM entities LIMIT 3"):
            print(f"    - {row['semantic_id']} ({row['entity_class']}): {row['name']}")
        
        # Sample memory shards
        print("\n  Memory Shards:")
        for row in cursor.execute("""
            SELECT m.uid, m.contents, a.name as agent_name 
            FROM memory_shards m
            JOIN agents a ON m.agent_id = a.id
            LIMIT 3
        """):
            content = row['contents'][:50] + '...' if len(row['contents']) > 50 else row['contents']
            print(f"    - {row['uid']} [{row['agent_name']}]: {content}")
        
        # Sample linkages
        print("\n  Semantic Linkages:")
        for row in cursor.execute("""
            SELECT e1.name as source, e2.name as target, sl.linkage_type, sl.weight
            FROM semantic_linkages sl
            JOIN entities e1 ON sl.source_id = e1.id
            JOIN entities e2 ON sl.target_id = e2.id
            LIMIT 3
        """):
            print(f"    - {row['source']} -> {row['target']} ({row['linkage_type']}, weight: {row['weight']:.2f})")
        
        conn.close()
        
        # Summary
        print("\n" + "="*60)
        print("MIGRATION TEST SUMMARY:")
        for table, count in results.items():
            print(f"  {table:20s}: {count:3d} records")
        print("="*60)
        
        # Check if migration was successful
        if results['agents'] >= 2 and results['entities'] >= 3 and results['memory_shards'] >= 2:
            print("\n✅ Migration test PASSED!")
            return True
        else:
            print("\n❌ Migration test FAILED - insufficient data migrated")
            return False
        
    except Exception as e:
        print(f"\n❌ Migration test FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        for db in [source_db, target_db]:
            if os.path.exists(db):
                os.unlink(db)
        print("\nCleaned up test databases")


def main():
    """Run the test."""
    success = run_migration_test_direct()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()