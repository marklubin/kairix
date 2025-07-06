"""
Functional tests to ensure parity between Neo4j and SQLite implementations.

These tests run the same operations against both databases and verify
that the results are equivalent.
"""
import pytest
from datetime import datetime
from typing import Any, Dict, List, Tuple
import logging

from kairix_core.runtime.storage import StorageRuntime
from kairix_core.database.neo4j_to_sqlite import Neo4jToSQLiteConverter
from kairix_core.cognition.stores.embedded_data import EmbeddedDataStore as Neo4jEmbeddedStore
from kairix_core.cognition.stores.sqlite_embedded_data import SQLiteEmbeddedDataStore
from kairix_core.cognition.perceptor.conversation_history import ConversationHistoryPerceptor as Neo4jConvHistory
from kairix_core.cognition.perceptor.sqlite_conversation_history import SQLiteConversationHistoryPerceptor
from kairix_core.types.cognition import Perception, Stimulus, StimulusType

logger = logging.getLogger(__name__)


class TestDatabaseParity:
    """Test that Neo4j and SQLite implementations produce equivalent results."""
    
    @pytest.fixture
    def neo4j_store(self):
        """Create a Neo4j embedded store for testing."""
        # This would connect to a test Neo4j instance
        pytest.skip("Neo4j test instance required")
        
    @pytest.fixture
    def sqlite_store(self, test_db):
        """Create a SQLite embedded store for testing."""
        from kairix_core.cognition.stores.sqlite_embedded_data import create_memory_shard_store
        return create_memory_shard_store(test_db.storage)
    
    def test_embedded_search_parity(self, neo4j_store, sqlite_store):
        """Test that vector search returns similar results from both stores."""
        test_query = "artificial intelligence and machine learning"
        
        # Get results from both stores
        neo4j_results = list(neo4j_store.search(test_query, k=5))
        sqlite_results = list(sqlite_store.search(test_query, k=5))
        
        # Verify same number of results
        assert len(neo4j_results) == len(sqlite_results)
        
        # Verify content similarity (not exact match due to potential scoring differences)
        neo4j_contents = {result[0] for result in neo4j_results}
        sqlite_contents = {result[0] for result in sqlite_results}
        
        overlap = neo4j_contents.intersection(sqlite_contents)
        assert len(overlap) >= len(neo4j_contents) * 0.8  # At least 80% overlap
    
    def test_conversation_history_parity(self):
        """Test that conversation history behaves identically."""
        # Create both perceptors
        neo4j_perceptor = pytest.skip("Neo4j test instance required")
        sqlite_perceptor = SQLiteConversationHistoryPerceptor(
            agent_name="test_agent",
            storage=StorageRuntime()
        )
        
        # Test stimuli
        stimuli = [
            Stimulus(type=StimulusType.user_message, content="Hello, how are you?"),
            Stimulus(type=StimulusType.self_perception, content="I'm doing well, thank you!"),
            Stimulus(type=StimulusType.user_message, content="What's the weather like?"),
        ]
        
        # Process through both systems
        neo4j_perceptions = []
        sqlite_perceptions = []
        
        for stimulus in stimuli:
            neo4j_perceptions.extend(neo4j_perceptor.perceive(stimulus))
            sqlite_perceptions.extend(sqlite_perceptor.perceive(stimulus))
        
        # Compare results
        assert len(neo4j_perceptions) == len(sqlite_perceptions)
        
        # Get recent context from both
        neo4j_context = neo4j_perceptor.get_recent_context(5)
        sqlite_context = sqlite_perceptor.get_recent_context(5)
        
        assert len(neo4j_context) == len(sqlite_context)
        assert neo4j_context == sqlite_context


class TestMigrationIntegrity:
    """Test that data migration preserves all information correctly."""
    
    @pytest.fixture
    def migration_converter(self):
        """Create a migration converter instance."""
        # Use test database URLs
        neo4j_url = "bolt://neo4j:password@localhost:7687/test"
        return Neo4jToSQLiteConverter(neo4j_url)
    
    def test_agent_migration(self, migration_converter):
        """Test that all agents are migrated correctly."""
        # Run migration
        migration_converter._convert_agents()
        
        # Verify counts match
        neo4j_count = pytest.skip("Neo4j count query")
        
        with migration_converter.storage.session() as session:
            from kairix_core.types.db import Agent
            sqlite_count = session.query(Agent).count()
        
        assert neo4j_count == sqlite_count
        
        # Verify agent names preserved
        assert "default" in migration_converter.agent_map
    
    def test_entity_migration(self, migration_converter):
        """Test that concepts are correctly migrated to entities."""
        migration_converter._convert_concepts_to_entities()
        
        # Check that all concepts were migrated
        assert len(migration_converter.concept_to_entity_map) > 0
        
        # Verify embedding dimensions
        with migration_converter.storage.session() as session:
            from kairix_core.types.db import Entity
            entity = session.query(Entity).first()
            if entity and entity.embedding:
                assert len(entity.embedding) == 128
    
    def test_linkage_migration(self, migration_converter):
        """Test semantic linkages are preserved."""
        # First convert entities
        migration_converter._convert_concepts_to_entities()
        # Then linkages
        migration_converter._convert_semantic_linkages()
        
        # Verify linkages exist
        with migration_converter.storage.session() as session:
            from kairix_core.types.db import SemanticLinkage
            linkage_count = session.query(SemanticLinkage).count()
            assert linkage_count > 0
    
    def test_memory_shard_migration(self, migration_converter):
        """Test memory shards are migrated with embeddings."""
        # Run prerequisite migrations
        migration_converter._convert_agents()
        migration_converter._convert_source_documents()
        migration_converter._convert_memory_shards()
        
        # Check memory shards
        with migration_converter.storage.session() as session:
            from kairix_core.types.db import MemoryShard
            shard = session.query(MemoryShard).first()
            
            if shard:
                assert shard.agent_id is not None
                assert len(shard.embedding) == 128
                assert shard.embedding_type == "kairix-default-128"


class TestFunctionalScenarios:
    """End-to-end functional tests for common use cases."""
    
    def test_memory_search_scenario(self, test_db):
        """Test a complete memory search scenario."""
        from kairix_core.cognition.stores.sqlite_embedded_data import create_memory_shard_store
        from kairix_core.types.db import Agent, MemoryShard
        
        store = create_memory_shard_store(test_db.storage)
        
        # Create test data
        with test_db.storage.session() as session:
            agent_dao = test_db.storage.get_dao(Agent, session)
            memory_dao = test_db.storage.get_dao(MemoryShard, session)
            
            agent = agent_dao.create(name="test_agent")
            session.flush()
            
            # Create test memories
            test_memories = [
                "I learned about quantum computing today",
                "The weather was beautiful this morning", 
                "I had a conversation about artificial intelligence",
                "Quantum mechanics is fascinating",
            ]
            
            for content in test_memories:
                memory = memory_dao.create(
                    contents=content,
                    embedding_type="kairix-default-128",
                    embedding=[0.1] * 128,  # Dummy embedding
                    agent_id=agent.id
                )
                session.flush()
                
                # Add to vector index if available
                if hasattr(store, 'add_item_with_embedding'):
                    store.add_item_with_embedding(memory.id, content)
            
            session.commit()
        
        # Search for quantum-related memories
        results = list(store.search("quantum physics", k=3, agent_id=agent.id))
        
        # Should find quantum-related memories
        assert len(results) > 0
        assert any("quantum" in content.lower() for content, _ in results)
    
    def test_conversation_flow_scenario(self, test_db):
        """Test a complete conversation flow."""
        from kairix_core.cognition.perceptor.sqlite_conversation_history import SQLiteConversationHistoryPerceptor
        
        perceptor = SQLiteConversationHistoryPerceptor(
            agent_name="assistant",
            storage=test_db.storage
        )
        
        # Simulate a conversation
        conversation = [
            ("user", "Hello, can you help me with Python?"),
            ("assistant", "Of course! I'd be happy to help you with Python."),
            ("user", "How do I read a file?"),
            ("assistant", "You can use the open() function..."),
        ]
        
        perceptions = []
        for role, content in conversation:
            stim_type = StimulusType.user_message if role == "user" else StimulusType.self_perception
            stimulus = Stimulus(type=stim_type, content=content)
            perceptions.extend(perceptor.perceive(stimulus))
        
        # Get recent context
        context = perceptor.get_recent_context(10)
        
        # Verify conversation preserved
        assert len(context) == len(conversation)
        
        # Verify order
        for i, (role, content) in enumerate(conversation):
            assert context[i]["role"] == role
            assert context[i]["content"] == content
    
    async def test_semantic_graph_scenario(self, test_db):
        """Test semantic graph traversal."""
        from kairix_core.cognition.perceptor.semantic_graph import SemanticGraphPerceptor
        from kairix_core.cognition.stores.sqlite_embedded_data import create_concept_store
        from kairix_core.types.db import Entity, SemanticLinkage, EntityClass, LinkageType
        
        # Create test graph
        with test_db.storage.session() as session:
            # Ensure entity classes and linkage types exist
            ec_dao = test_db.storage.get_dao(EntityClass, session)
            lt_dao = test_db.storage.get_dao(LinkageType, session)
            
            if not ec_dao.find_one_by(name="concept"):
                ec_dao.create(name="concept", description="Abstract concept")
            
            if not lt_dao.find_one_by(name="related_to"):
                lt_dao.create(name="related_to", description="General relation")
            
            session.flush()
            
            # Create entities
            entity_dao = test_db.storage.get_dao(Entity, session)
            
            ai = entity_dao.create(
                semantic_id="artificial_intelligence",
                name="Artificial Intelligence",
                entity_class="concept",
                embedding_type="kairix-default-128",
                embedding=[0.2] * 128
            )
            
            ml = entity_dao.create(
                semantic_id="machine_learning", 
                name="Machine Learning",
                entity_class="concept",
                embedding_type="kairix-default-128",
                embedding=[0.3] * 128
            )
            
            session.flush()
            
            # Create linkage
            linkage_dao = test_db.storage.get_dao(SemanticLinkage, session)
            linkage_dao.create(
                source_id=ai.id,
                target_id=ml.id,
                linkage_type="related_to",
                weight=0.9
            )
            
            session.commit()
        
        # Create perceptor
        store = create_concept_store(test_db.storage)
        perceptor = SemanticGraphPerceptor(store, test_db.storage)
        
        # Test perception
        stimulus = Stimulus(
            type=StimulusType.user_message,
            content="Tell me about artificial intelligence"
        )
        
        perceptions = await perceptor.perceive(stimulus)
        
        # Should find related concepts
        assert len(perceptions) > 0


def test_migration_end_to_end():
    """Test complete migration process."""
    # This would be run against a real Neo4j instance with test data
    pytest.skip("Requires Neo4j test instance")
    
    converter = Neo4jToSQLiteConverter("bolt://neo4j:password@localhost:7687/test")
    
    # Run full migration
    converter.convert_all()
    
    # Verify all data migrated
    assert len(converter.agent_map) > 0
    assert len(converter.concept_to_entity_map) > 0
    assert len(converter.source_doc_map) > 0
    
    # Run parity tests
    # ... would run the parity tests above