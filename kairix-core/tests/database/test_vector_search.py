"""
Test vector search functionality with SQLite VSS.
"""
import pytest
from kairix_core.types.db import Entity, EntityClass, EmbeddingType, Agent, MemoryShard


def test_vector_search_entities(test_db):
    """Test vector similarity search for entities"""
    # Skip if VSS not available
    if not hasattr(test_db, 'vector_dao') or test_db.vector_dao is None:
        pytest.skip("Vector search not available")
    
    with test_db.session() as session:
        # Setup
        entity_class_dao = test_db.get_dao(EntityClass, session)
        # Check if entity class already exists before creating
        if not entity_class_dao.find_one_by(name="person"):
            entity_class_dao.create(name="person")
        
        embedding_dao = test_db.get_dao(EmbeddingType, session)
        # Check if embedding type already exists before creating
        if not embedding_dao.find_one_by(name="test-embedding"):
            embedding_dao.create(
                name="test-embedding",
                model_name="test",
                vector_length=128
            )
        
        entity_dao = test_db.get_dao(Entity, session)
        
        # Create entities with different embeddings
        john = entity_dao.create(
            semantic_id="john",
            name="John Doe",
            entity_class="person",
            embedding_type="test-embedding",
            embedding=[1.0] * 128  # All 1s
        )
        
        jane = entity_dao.create(
            semantic_id="jane",
            name="Jane Smith",
            entity_class="person",
            embedding_type="test-embedding",
            embedding=[0.5] * 128  # All 0.5s
        )
        
        bob = entity_dao.create(
            semantic_id="bob",
            name="Bob Johnson",
            entity_class="person",
            embedding_type="test-embedding",
            embedding=[0.1] * 128  # All 0.1s
        )
        
        session.flush()
        
        # Add to vector index
        test_db.vector_dao.add_entity_embedding(john.id, john.embedding)
        test_db.vector_dao.add_entity_embedding(jane.id, jane.embedding)
        test_db.vector_dao.add_entity_embedding(bob.id, bob.embedding)
        
        # Search with query closer to John (0.9s)
        query = [0.9] * 128
        results = test_db.vector_dao.search_similar_entities(query, limit=3)
        
        # John should be first (closest to 0.9)
        assert len(results) > 0
        assert results[0][0] == john.id  # First result should be John
        
        # Test removal
        test_db.vector_dao.remove_entity_embedding(bob.id)
        results = test_db.vector_dao.search_similar_entities([0.1] * 128, limit=3)
        entity_ids = [r[0] for r in results]
        assert bob.id not in entity_ids


def test_vector_search_memories(test_db):
    """Test vector similarity search for memory shards"""
    # Vector search is now always available
    assert test_db.vector_dao is not None, "Vector search must be enabled"
    
    with test_db.session() as session:
        # Setup
        agent_dao = test_db.get_dao(Agent, session)
        agent1 = agent_dao.create(name="agent1")
        agent2 = agent_dao.create(name="agent2")
        
        embedding_dao = test_db.get_dao(EmbeddingType, session)
        # Check if embedding type already exists before creating
        if not embedding_dao.find_one_by(name="memory-embedding"):
            embedding_dao.create(
                name="memory-embedding",
                model_name="test",
                vector_length=128
            )
        
        memory_dao = test_db.get_dao(MemoryShard, session)
        
        # Create memories for different agents
        memory1 = memory_dao.create(
            contents="Agent 1 memory about coding",
            embedding_type="memory-embedding",
            embedding=[1.0, 0.0] + [0.0] * 126,
            agent_id=agent1.id
        )
        
        memory2 = memory_dao.create(
            contents="Agent 1 memory about food",
            embedding_type="memory-embedding",
            embedding=[0.0, 1.0] + [0.0] * 126,
            agent_id=agent1.id
        )
        
        memory3 = memory_dao.create(
            contents="Agent 2 memory",
            embedding_type="memory-embedding",
            embedding=[0.5, 0.5] + [0.0] * 126,
            agent_id=agent2.id
        )
        
        session.flush()
        
        # Add to vector index
        test_db.vector_dao.add_memory_embedding(memory1.id, memory1.embedding)
        test_db.vector_dao.add_memory_embedding(memory2.id, memory2.embedding)
        test_db.vector_dao.add_memory_embedding(memory3.id, memory3.embedding)
        
        # Search all memories
        query = [0.9, 0.1] + [0.0] * 126  # Closer to memory1
        results = test_db.vector_dao.search_similar_memories(query, limit=3)
        assert len(results) == 3
        assert results[0][0] == memory1.id  # Should be closest
        
        # Search only agent1's memories
        results = test_db.vector_dao.search_similar_memories(
            query, limit=3, agent_id=agent1.id
        )
        assert len(results) == 2  # Only agent1's memories
        memory_ids = [r[0] for r in results]
        assert memory3.id not in memory_ids  # Agent2's memory excluded