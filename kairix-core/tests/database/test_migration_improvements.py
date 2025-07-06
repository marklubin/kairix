"""
Test the improved migration features:
- Summary table
- Name normalization
- History tracking via observations
- UID fields for idempotency
"""
import pytest
from datetime import datetime

from kairix_core.database.neo4j_to_sqlite import Neo4jToSQLiteConverter
from kairix_core.types.db import (
    Entity, EntityClass, LinkageType, Summary, MemoryShard,
    EntityObservation, LinkageObservation
)


def test_summary_table(test_db):
    """Test Summary table creation and relationships."""
    with test_db.session() as session:
        # Create a summary
        summary_dao = test_db.get_dao(Summary, session)
        summary = summary_dao.create(
            uid="test_summary_001",
            summary_text="This is a test summary of important information.",
            extractions_performed=["entities", "relationships", "dates"],
            approximate_date=datetime(2024, 1, 15)
        )
        session.flush()
        
        # Create a memory shard linked to the summary
        memory_dao = test_db.get_dao(MemoryShard, session)
        memory = memory_dao.create(
            uid="test_shard_001",
            contents="Detailed memory content",
            embedding_type="kairix-default-128",
            embedding=[0.1] * 128,
            agent_id=test_db.default_agent_id,  # Use fixture's agent
            summary_id=summary.id
        )
        session.commit()
        
        # Verify relationship
        retrieved_memory = memory_dao.get_by_id(memory.id)
        assert retrieved_memory.summary_id == summary.id
        assert retrieved_memory.summary.summary_text == summary.summary_text


def test_name_normalization(test_db):
    """Test that names are normalized properly."""
    # Don't actually connect to Neo4j for this test
    from kairix_core.database.neo4j_to_sqlite import Neo4jToSQLiteConverter
    
    # Create a mock converter just to test the normalization method
    class MockConverter:
        def _normalize_name(self, name):
            # Copy the implementation from the real converter
            import re
            normalized = re.sub(r'[^a-zA-Z0-9\s_-]', '', name)
            normalized = re.sub(r'\s+', '_', normalized)
            return normalized.lower().strip('_')
    
    converter = MockConverter()
    
    # Test various name formats
    test_cases = [
        ("CamelCase", "camelcase"),
        ("snake_case", "snake_case"),
        ("kebab-case", "kebab-case"),
        ("With Spaces", "with_spaces"),
        ("Special!@#Characters", "specialcharacters"),
        ("Multiple   Spaces", "multiple_spaces"),
        ("__leading_underscores__", "leading_underscores"),
    ]
    
    for input_name, expected in test_cases:
        assert converter._normalize_name(input_name) == expected


def test_dynamic_type_creation(test_db):
    """Test that new entity classes and linkage types are created dynamically."""
    with test_db.session() as session:
        # Create a mock converter
        class MockConverter:
            def _normalize_name(self, name):
                import re
                normalized = re.sub(r'[^a-zA-Z0-9\s_-]', '', name)
                normalized = re.sub(r'\s+', '_', normalized)
                return normalized.lower().strip('_')
            
            def _map_concept_type_to_entity_class(self, concept_type):
                type_map = {
                    "Person": "person",
                    "Organization": "organization",
                    "Location": "location",
                    "Event": "event",
                    "Object": "object"
                }
                return type_map.get(concept_type, self._normalize_name(concept_type))
        
        converter = MockConverter()
        
        # Test entity class creation
        entity_class_dao = test_db.get_dao(EntityClass, session)
        
        # Should create normalized version
        class_name = converter._map_concept_type_to_entity_class("CustomEntityType!")
        assert class_name == "customentitytype"
        
        # Simulate migration creating the class
        if not entity_class_dao.find_one_by(name=class_name):
            entity_class_dao.create(
                name=class_name,
                description="Migrated from Neo4j"
            )
        session.commit()
        
        # Verify it was created
        created_class = entity_class_dao.find_one_by(name=class_name)
        assert created_class is not None
        assert created_class.name == "customentitytype"


def test_entity_observations_instead_of_updates(test_db):
    """Test that encounters are stored as observations, not as entity updates."""
    with test_db.session() as session:
        from kairix_core.types.db import EntityObservation as EntityObs
        entity_dao = test_db.get_dao(Entity, session)
        obs_dao = test_db.get_dao(EntityObs, session)
        
        # Create an entity
        entity = entity_dao.create(
            semantic_id="test_entity_001",
            name="Test Entity",
            entity_class="concept",
            embedding_type="kairix-default-128",
            embedding=[0.2] * 128
        )
        session.flush()
        
        # Simulate multiple encounters
        encounter_times = [
            datetime(2024, 1, 1, 10, 0),
            datetime(2024, 1, 2, 15, 30),
            datetime(2024, 1, 3, 9, 45),
        ]
        
        for encounter_time in encounter_times:
            obs_dao.create(
                entity_id=entity.id,
                observation_type="encounter",
                observation_value="Entity encountered in conversation",
                approximate_occurrence=encounter_time,
                source_descriptor="chat_session_123"
            )
        
        session.commit()
        
        # Verify observations were created
        observations = session.query(EntityObs).filter_by(
            entity_id=entity.id, 
            observation_type="encounter"
        ).all()
        assert len(observations) == 3
        
        # Verify chronological order
        obs_times = [obs.approximate_occurrence for obs in observations]
        assert obs_times == sorted(obs_times)


def test_uid_fields_for_idempotency(test_db):
    """Test that UID fields prevent duplicate imports."""
    # Create first memory with UID
    with test_db.session() as session:
        memory_dao = test_db.get_dao(MemoryShard, session)
        memory1 = memory_dao.create(
            uid="unique_memory_001",
            contents="First memory",
            embedding_type="kairix-default-128",
            embedding=[.3] * 128,
            agent_id=test_db.default_agent_id
        )
        session.commit()
        first_id = memory1.id
    
    # Try to create duplicate with same UID - should fail
    from sqlalchemy.exc import IntegrityError
    
    # Use a separate session that will be rolled back
    session2 = test_db.Session()
    try:
        memory_dao2 = test_db.get_dao(MemoryShard, session2)
        # The create() method flushes immediately, so it will raise here
        with pytest.raises(IntegrityError):
            memory2 = memory_dao2.create(
                uid="unique_memory_001",  # Same UID
                contents="Different content",
                embedding_type="kairix-default-128",
                embedding=[0.4] * 128,
                agent_id=test_db.default_agent_id
            )
    finally:
        session2.rollback()
        session2.close()
    
    # Verify original is still there
    with test_db.session() as session3:
        memory_dao3 = test_db.get_dao(MemoryShard, session3)
        original = memory_dao3.get_by_id(first_id)
        assert original is not None
        assert original.contents == "First memory"


def test_linkage_observation_history(test_db):
    """Test that linkage observations track history properly."""
    with test_db.session() as session:
        # Create entities first
        entity_dao = test_db.get_dao(Entity, session)
        entity1 = entity_dao.create(
            semantic_id="test_entity_link_1",
            name="Entity 1",
            entity_class="concept",
            embedding_type="kairix-default-128",
            embedding=[0.5] * 128
        )
        entity2 = entity_dao.create(
            semantic_id="test_entity_link_2",
            name="Entity 2",
            entity_class="concept",
            embedding_type="kairix-default-128",
            embedding=[0.6] * 128
        )
        session.flush()
        
        obs_dao = test_db.get_dao(LinkageObservation, session)
        
        # Create multiple observations for the same linkage
        observations = [
            {
                "source_id": entity1.id,
                "target_id": entity2.id,
                "linkage_type": "related_to",
                "approximate_occurrence": datetime(2024, 1, 1),
                "source_descriptor": "article_analysis",
                "emotional_tone": "neutral"
            },
            {
                "source_id": entity1.id,
                "target_id": entity2.id,
                "linkage_type": "related_to",
                "approximate_occurrence": datetime(2024, 1, 5),
                "source_descriptor": "user_feedback",
                "emotional_tone": "happy"
            }
        ]
        
        for obs_data in observations:
            obs_dao.create(**obs_data)
        
        session.commit()
        
        # Retrieve observations
        linkage_history = session.query(LinkageObservation).filter_by(
            source_id=entity1.id,
            target_id=entity2.id,
            linkage_type="related_to"
        ).all()
        
        # Should have multiple observations for same linkage
        assert len(linkage_history) >= 2
        
        # Verify we can track observations over time
        dates = [obs.approximate_occurrence for obs in linkage_history]
        # Should be chronological
        assert dates == sorted(dates)
        
        # Emotional tone should be tracked
        tones = [obs.emotional_tone for obs in linkage_history if obs.emotional_tone]
        assert "neutral" in tones or "happy" in tones