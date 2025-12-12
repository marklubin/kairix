#!/usr/bin/env python3
"""
Test Neo4j connection and check stored data
"""
from neomodel import db
from apiana import runtime_config
from apiana.storage.neo4j_store import AgentMemoryStore
from apiana.types.memory_block import Block, Tag, Grounding

def test_neo4j_connection():
    """Test Neo4j connection and show stored data."""
    print("Testing Neo4j Connection")
    print("=" * 40)
    
    # Show configuration
    print("Neo4j Config:")
    print(f"  Host: {runtime_config.neo4j.host}")
    print(f"  Port: {runtime_config.neo4j.port}")
    print(f"  Database: {runtime_config.neo4j.database}")
    print(f"  Username: {runtime_config.neo4j.username}")
    print("")
    
    try:
        # Initialize store
        memory_store = AgentMemoryStore(runtime_config.neo4j)
        print("✅ Successfully connected to Neo4j")
        
        # Test basic query
        result = db.cypher_query("MATCH (n) RETURN count(n) as total_nodes")[0]
        total_nodes = result[0][0] if result else 0
        print(f"📊 Total nodes in database: {total_nodes}")
        
        # Check for Block nodes
        blocks = Block.nodes.all()
        print(f"🧠 Memory blocks found: {len(blocks)}")
        
        if blocks:
            print("\nRecent blocks:")
            for i, block in enumerate(blocks[-5:]):  # Show last 5
                print(f"  {i+1}. Type: {block.block_type}, Created: {block.created_at}")
                print(f"     Content preview: {block.content[:100]}...")
                print("")
        
        # Check for Tags
        tags = Tag.nodes.all()
        print(f"🏷️  Tags found: {len(tags)}")
        
        if tags:
            print("Tags:", [tag.name for tag in tags[:10]])  # Show first 10
        
        # Check for Groundings
        groundings = Grounding.nodes.all()
        print(f"🔗 Groundings found: {len(groundings)}")
        
        if groundings:
            print("Recent groundings:")
            for i, grounding in enumerate(groundings[-3:]):  # Show last 3
                print(f"  {i+1}. {grounding.external_label} ({grounding.external_source})")
        
        # Run a more detailed query
        print("\n" + "=" * 40)
        print("Detailed Memory Structure:")
        
        query = """
        MATCH (b:Block)-[:GROUNDED_BY]->(g:Grounding)
        OPTIONAL MATCH (b)-[:TAGGED_WITH]->(t:Tag)
        RETURN b.block_type, b.experience_type, g.external_label, 
               collect(DISTINCT t.name) as tags, 
               b.created_at
        ORDER BY b.created_at DESC
        LIMIT 10
        """
        
        results = db.cypher_query(query)[0]
        
        if results:
            for result in results:
                block_type, exp_type, label, tags, created = result
                print(f"• {block_type}/{exp_type}: {label}")
                print(f"  Tags: {tags}")
                print(f"  Created: {created}")
                print("")
        else:
            print("No memory blocks found with relationships.")
            
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to Neo4j: {e}")
        return False

def show_database_schema():
    """Show the current database schema."""
    print("\n" + "=" * 40)
    print("Database Schema:")
    
    try:
        # Get all labels
        labels_query = "CALL db.labels()"
        labels_result = db.cypher_query(labels_query)[0]
        labels = [row[0] for row in labels_result]
        print(f"Node Labels: {labels}")
        
        # Get all relationship types
        rels_query = "CALL db.relationshipTypes()"
        rels_result = db.cypher_query(rels_query)[0]
        relationships = [row[0] for row in rels_result]
        print(f"Relationship Types: {relationships}")
        
        # Get some sample data structure
        if 'Block' in labels:
            sample_query = """
            MATCH (b:Block)
            RETURN keys(b) as properties
            LIMIT 1
            """
            sample_result = db.cypher_query(sample_query)[0]
            if sample_result:
                properties = sample_result[0][0]
                print(f"Block Properties: {properties}")
        
    except Exception as e:
        print(f"Error getting schema: {e}")

if __name__ == "__main__":
    success = test_neo4j_connection()
    if success:
        show_database_schema()
    else:
        print("\nTroubleshooting:")
        print("1. Check if Neo4j is running: docker-compose up -d")
        print("2. Verify connection settings in configuration")
        print("3. Check if data was actually processed and stored")