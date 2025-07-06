"""
Test SQLite embedded data store with vector search.
"""
import pytest
from kairix_core.cognition.stores.sqlite_embedded_data import (
    SQLiteEmbeddedDataStore,
    create_memory_shard_store,
    create_concept_store
)
from kairix_core.types.db import (
    Entity, EntityClass, EmbeddingType, Agent, MemoryShard
)


def test_memory_shard_vector_search(test_db):
    """Test vector search for memory shards."""
    # Skip if VSS not available
    if not hasattr(test_db, 'vector_dao') or test_db.vector_dao is None:
        pytest.skip("Vector search not available")
    
    with test_db.session() as session:
        # Setup
        agent_dao = test_db.get_dao(Agent, session)
        agent = agent_dao.create(name="test_agent")
        
        embedding_dao = test_db.get_dao(EmbeddingType, session)
        embedding_dao.create(
            name="test-embedding",
            model_name="test",
            vector_length=128
        )
        
        memory_dao = test_db.get_dao(MemoryShard, session)
        
        # Create memory shards with different content
        memory1 = memory_dao.create(
            contents="I love programming in Python",
            embedding_type="test-embedding",
            embedding=[1.0] * 128,
            agent_id=agent.id
        )
        
        memory2 = memory_dao.create(
            contents="Pizza is my favorite food",
            embedding_type="test-embedding",
            embedding=[0.5] * 128,
            agent_id=agent.id
        )
        
        memory3 = memory_dao.create(
            contents="Machine learning is fascinating",
            embedding_type="test-embedding",
            embedding=[0.8] * 128,
            agent_id=agent.id
        )
        
        session.commit()
    
    # Create store and add embeddings
    store = create_memory_shard_store(storage=test_db)
    
    # Add to vector index
    store.add_item_with_embedding(memory1.id, memory1.contents, memory1.embedding)
    store.add_item_with_embedding(memory2.id, memory2.contents, memory2.embedding)
    store.add_item_with_embedding(memory3.id, memory3.contents, memory3.embedding)
    
    # Search for programming-related content
    # Since we're using dummy embeddings, we'll search with a pattern close to memory1
    results = list(store.search("programming", k=2))
    
    assert len(results) == 2
    # First result should have highest score
    assert results[0][1] > results[1][1]
    # Content should be returned
    assert "programming" in results[0][0] or "learning" in results[0][0]


def test_entity_vector_search(test_db):
    """Test vector search for entities."""
    # Skip if VSS not available
    if not hasattr(test_db, 'vector_dao') or test_db.vector_dao is None:
        pytest.skip("Vector search not available")
    
    with test_db.session() as session:
        # Setup
        entity_class_dao = test_db.get_dao(EntityClass, session)
        entity_class_dao.create(name="person")
        
        embedding_dao = test_db.get_dao(EmbeddingType, session)
        embedding_dao.create(
            name="test-embedding",
            model_name="test",
            vector_length=128
        )
        
        entity_dao = test_db.get_dao(Entity, session)
        
        # Create entities
        john = entity_dao.create(
            semantic_id="person://john_doe",
            name="John Doe",
            entity_class="person",
            embedding_type="test-embedding",
            embedding=[1.0, 0.0] + [0.0] * 126
        )
        
        jane = entity_dao.create(
            semantic_id="person://jane_smith",
            name="Jane Smith",
            entity_class="person",
            embedding_type="test-embedding",
            embedding=[0.0, 1.0] + [0.0] * 126
        )
        
        bob = entity_dao.create(
            semantic_id="person://bob_johnson",
            name="Bob Johnson",
            entity_class="person",
            embedding_type="test-embedding",
            embedding=[0.5, 0.5] + [0.0] * 126
        )
        
        session.commit()
    
    # Create store and add embeddings
    store = create_concept_store(storage=test_db)
    
    # Add to vector index
    store.add_item_with_embedding(john.id, john.name, john.embedding)
    store.add_item_with_embedding(jane.id, jane.name, jane.embedding)
    store.add_item_with_embedding(bob.id, bob.name, bob.embedding)
    
    # Search - should return semantic_id as content
    results = list(store.search("find similar", k=3))
    
    assert len(results) == 3
    # Check that semantic IDs are returned
    semantic_ids = [r[0] for r in results]
    assert "person://john_doe" in semantic_ids
    assert "person://jane_smith" in semantic_ids
    assert "person://bob_johnson" in semantic_ids


def test_content_transform(test_db):
    """Test content transformation in search results."""
    # Skip if VSS not available
    if not hasattr(test_db, 'vector_dao') or test_db.vector_dao is None:
        pytest.skip("Vector search not available")
    
    with test_db.session() as session:
        # Setup
        entity_class_dao = test_db.get_dao(EntityClass, session)
        entity_class_dao.create(name="test")
        
        embedding_dao = test_db.get_dao(EmbeddingType, session)
        embedding_dao.create(
            name="test-embedding",
            model_name="test",
            vector_length=128
        )
        
        entity_dao = test_db.get_dao(Entity, session)
        entity = entity_dao.create(
            semantic_id="test://example",
            name="Example Entity",
            entity_class="test",
            embedding_type="test-embedding",
            embedding=[1.0] * 128
        )
        session.commit()
    
    # Create store with content transform
    def transform_semantic_id(semantic_id):
        # Extract just the name part after ://
        return semantic_id.split("://")[1]
    
    store = SQLiteEmbeddedDataStore(
        table_name='entity',
        content_key='semantic_id',
        embedding_dims=128,
        content_transform=transform_semantic_id,
        storage=test_db
    )
    
    # Add to index
    store.add_item_with_embedding(entity.id, entity.name, entity.embedding)
    
    # Search
    results = list(store.search("test", k=1))
    
    assert len(results) == 1
    # Content should be transformed
    assert results[0][0] == "example"  # Not "test://example"


def test_agent_filtering_memory_search(test_db):
    """Test that memory search can be filtered by agent."""
    # Skip if VSS not available
    if not hasattr(test_db, 'vector_dao') or test_db.vector_dao is None:
        pytest.skip("Vector search not available")
    
    with test_db.session() as session:
        # Create two agents
        agent_dao = test_db.get_dao(Agent, session)
        agent1 = agent_dao.create(name="agent1")
        agent2 = agent_dao.create(name="agent2")
        
        embedding_dao = test_db.get_dao(EmbeddingType, session)
        embedding_dao.create(
            name="test-embedding",
            model_name="test",
            vector_length=128
        )
        
        memory_dao = test_db.get_dao(MemoryShard, session)
        
        # Create memories for different agents
        memory1 = memory_dao.create(
            contents="Agent 1 memory",
            embedding_type="test-embedding",
            embedding=[1.0] * 128,
            agent_id=agent1.id
        )
        
        memory2 = memory_dao.create(
            contents="Agent 2 memory",
            embedding_type="test-embedding",
            embedding=[1.0] * 128,  # Same embedding
            agent_id=agent2.id
        )
        
        session.commit()
    
    store = create_memory_shard_store(storage=test_db)
    
    # Add both to index
    store.add_item_with_embedding(memory1.id, memory1.contents, memory1.embedding)
    store.add_item_with_embedding(memory2.id, memory2.contents, memory2.embedding)
    
    # Search with agent filter
    results = list(store.search("memory", k=10, agent_id=agent1.id))
    
    # Should only return agent1's memory
    assert len(results) == 1
    assert "Agent 1" in results[0][0]
    assert "Agent 2" not in results[0][0]