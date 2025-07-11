"""
Basic database tests to verify all tables and relationships work correctly.
"""

from kairix_core.types.db import (
    Entity, EntityClass, EmbeddingType, EntityObservation,
    LinkageType, EmotionalTone, SemanticLinkage, Agent, Source, SourceObject, MemoryShard
)


def test_create_reference_tables(test_db):
    """Test creating entries in reference tables"""
    with test_db.session() as session:
        # Create EntityClass
        entity_class_dao = test_db.get_dao(EntityClass, session)
        # Try to get existing or create new
        person_class = entity_class_dao.find_one_by(name="person")
        if not person_class:
            person_class = entity_class_dao.create(
                name="person",
                description="A human being",
                positive_examples="John Doe, Jane Smith",
                negative_examples="Apple Inc, New York City"
            )
        assert person_class.name == "person"
        
        # Create LinkageType
        linkage_dao = test_db.get_dao(LinkageType, session)
        # Create a unique linkage type for this test
        knows_type = linkage_dao.create(
            name="test_knows",
            description="Personal acquaintance",
            positive_examples="friends, colleagues",
            negative_examples="heard of, read about"
        )
        assert knows_type.name == "test_knows"
        
        # Create EmotionalTone
        emotion_dao = test_db.get_dao(EmotionalTone, session)
        # Create a unique emotional tone for this test
        happy_tone = emotion_dao.create(
            name="test_happy",
            description="Positive emotional state",
            positive_examples="joyful, excited, pleased",
            negative_examples="sad, angry, frustrated"
        )
        assert happy_tone.name == "test_happy"
        
        # Create EmbeddingType (use test prefix to avoid conflicts)
        embedding_dao = test_db.get_dao(EmbeddingType, session)
        ada_embedding = embedding_dao.create(
            name="test-text-embedding-ada-002",
            model_name="openai/text-embedding-ada-002",
            vector_length=1536
        )
        assert ada_embedding.vector_length == 1536


def test_create_entities(test_db):
    """Test creating entities with embeddings"""
    with test_db.session() as session:
        # First create required reference data
        entity_class_dao = test_db.get_dao(EntityClass, session)
        # Check if person already exists
        if not entity_class_dao.find_one_by(name="person"):
            entity_class_dao.create(name="person")
        
        embedding_dao = test_db.get_dao(EmbeddingType, session)
        embedding_dao.create(
            name="test-embedding",
            model_name="test",
            vector_length=128
        )
        
        # Create entities
        entity_dao = test_db.get_dao(Entity, session)
        john = entity_dao.create(
            semantic_id="person_john_doe",
            name="John Doe",
            entity_class="person",
            embedding_type="test-embedding",
            embedding=[0.1] * 128  # Dummy embedding
        )
        
        jane = entity_dao.create(
            semantic_id="person_jane_smith",
            name="Jane Smith",
            entity_class="person",
            embedding_type="test-embedding",
            embedding=[0.2] * 128
        )
        
        assert john.id is not None
        assert jane.id is not None
        assert john.name == "John Doe"
        assert jane.name == "Jane Smith"


def test_create_semantic_linkages(test_db):
    """Test creating semantic linkages between entities"""
    with test_db.session() as session:
        # Setup reference data
        entity_class_dao = test_db.get_dao(EntityClass, session)
        if not entity_class_dao.find_one_by(name="person"):
            entity_class_dao.create(name="person")
        
        linkage_dao = test_db.get_dao(LinkageType, session)
        if not linkage_dao.find_one_by(name="knows"):
            linkage_dao.create(name="knows")
        
        # Create entities
        entity_dao = test_db.get_dao(Entity, session)
        john = entity_dao.create(
            semantic_id="john", name="John", entity_class="person"
        )
        jane = entity_dao.create(
            semantic_id="jane", name="Jane", entity_class="person"
        )
        
        # Create linkage
        linkage_dao = test_db.get_dao(SemanticLinkage, session)
        linkage_dao.create(
            source_id=john.id,
            target_id=jane.id,
            linkage_type="knows",
            weight=5
        )
        
        # Verify
        found_links = linkage_dao.find_by(source_id=john.id)
        assert len(found_links) == 1
        assert found_links[0].target_id == jane.id


def test_create_observations(test_db):
    """Test creating entity and linkage observations"""
    with test_db.session() as session:
        # Setup
        entity_class_dao = test_db.get_dao(EntityClass, session)
        if not entity_class_dao.find_one_by(name="person"):
            entity_class_dao.create(name="person")
        
        emotion_dao = test_db.get_dao(EmotionalTone, session)
        if not emotion_dao.find_one_by(name="neutral"):
            emotion_dao.create(name="neutral")
        
        entity_dao = test_db.get_dao(Entity, session)
        john = entity_dao.create(
            semantic_id="john", name="John", entity_class="person"
        )
        
        # Create entity observation
        obs_dao = test_db.get_dao(EntityObservation, session)
        observation = obs_dao.create(
            entity_id=john.id,
            observation_type="name_change",
            observation_value="John Doe",
            emotional_tone="neutral",
            source_descriptor="user_input"
        )
        
        assert observation.entity_id == john.id
        assert observation.observation_type == "name_change"


def test_create_sources_and_memory(test_db):
    """Test creating sources, source objects, and memory shards"""
    with test_db.session() as session:
        # Create agent with unique name
        agent_dao = test_db.get_dao(Agent, session)
        import uuid
        agent = agent_dao.create(name=f"test_agent_{uuid.uuid4().hex[:8]}")
        
        # Create source
        source_dao = test_db.get_dao(Source, session)
        file_source = source_dao.create(
            name="documents_folder",
            source_type="filesystem",
            format="txt",
            processing_class="TextProcessor",
            configuration='{"path": "/docs"}'
        )
        
        # Create source object
        obj_dao = test_db.get_dao(SourceObject, session)
        doc = obj_dao.create(
            source_id=file_source.id,
            object_path="/docs/important.txt",
            content="This is important information",
            content_hash="abc123",
            extra_data='{"type": "document"}'
        )
        
        # Create embedding type
        embedding_dao = test_db.get_dao(EmbeddingType, session)
        embedding_dao.create(
            name="memory-embedding",
            model_name="test",
            vector_length=128
        )
        
        # Create memory shard
        memory_dao = test_db.get_dao(MemoryShard, session)
        memory = memory_dao.create(
            contents="Remember: This is important",
            embedding_type="memory-embedding",
            embedding=[0.3] * 128,
            agent_id=agent.id,
            source_object_id=doc.id
        )
        
        assert memory.agent_id == agent.id
        assert memory.source_object_id == doc.id


def test_dao_operations(test_db):
    """Test various DAO operations"""
    with test_db.session() as session:
        # Setup
        entity_class_dao = test_db.get_dao(EntityClass, session)
        if not entity_class_dao.find_one_by(name="place"):
            entity_class_dao.create(name="place")
        if not entity_class_dao.find_one_by(name="person"):
            entity_class_dao.create(name="person")
        
        # Test count (accounting for pre-initialized data)
        count = entity_class_dao.count()
        assert count >= 2  # At least place and person
        
        # Test find_by
        places = entity_class_dao.find_by(name="place")
        assert len(places) == 1
        
        # Test exists
        exists = entity_class_dao.exists(name="person")
        assert exists is True
        
        exists = entity_class_dao.exists(name="animal")
        assert exists is False
        
        # Test update
        place = entity_class_dao.find_one_by(name="place")
        entity_class_dao.update(place, description="A location or area")
        
        updated = entity_class_dao.get_by_id("place")
        assert updated.description == "A location or area"
        
        # Test delete
        initial_count = entity_class_dao.count()
        entity_class_dao.delete_by_id("place")
        count = entity_class_dao.count()
        assert count == initial_count - 1  # One less than before