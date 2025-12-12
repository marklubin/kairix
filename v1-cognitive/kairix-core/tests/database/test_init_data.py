"""
Test database initialization with default data.
"""
from kairix_core.database.init_data import (
    initialize_database,
    init_embedding_types,
    init_entity_classes,
    init_linkage_types,
    init_emotional_tones,
    init_default_agents
)
from kairix_core.types.db import (
    EmbeddingType, EntityClass, LinkageType, EmotionalTone, Agent
)


def test_init_embedding_types(empty_test_db):
    """Test initialization of embedding types."""
    init_embedding_types(empty_test_db)
    
    with empty_test_db.session() as session:
        embedding_dao = empty_test_db.get_dao(EmbeddingType, session)
        
        # Check that embeddings were created
        assert embedding_dao.count() >= 3
        
        # Check specific embeddings
        ada = embedding_dao.find_one_by(name="text-embedding-ada-002")
        assert ada is not None
        assert ada.vector_length == 1536
        
        mpnet = embedding_dao.find_one_by(name="sentence-transformers/all-mpnet-base-v2")
        assert mpnet is not None
        assert mpnet.vector_length == 768
        
        kairix = embedding_dao.find_one_by(name="kairix-default-128")
        assert kairix is not None
        assert kairix.vector_length == 128


def test_init_entity_classes(empty_test_db):
    """Test initialization of entity classes."""
    init_entity_classes(empty_test_db)
    
    with empty_test_db.session() as session:
        entity_class_dao = empty_test_db.get_dao(EntityClass, session)
        
        # Check count
        assert entity_class_dao.count() >= 6
        
        # Check specific classes
        person = entity_class_dao.find_one_by(name="person")
        assert person is not None
        assert "human being" in person.description
        
        org = entity_class_dao.find_one_by(name="organization")
        assert org is not None
        
        location = entity_class_dao.find_one_by(name="location")
        assert location is not None


def test_init_linkage_types(empty_test_db):
    """Test initialization of linkage types."""
    init_linkage_types(empty_test_db)
    
    with empty_test_db.session() as session:
        linkage_dao = empty_test_db.get_dao(LinkageType, session)
        
        # Check count
        assert linkage_dao.count() >= 6
        
        # Check specific types
        knows = linkage_dao.find_one_by(name="knows")
        assert knows is not None
        assert "acquaintance" in knows.description
        
        synonym = linkage_dao.find_one_by(name="synonym")
        assert synonym is not None
        
        antonym = linkage_dao.find_one_by(name="antonym")
        assert antonym is not None


def test_init_emotional_tones(empty_test_db):
    """Test initialization of emotional tones."""
    init_emotional_tones(empty_test_db)
    
    with empty_test_db.session() as session:
        emotion_dao = empty_test_db.get_dao(EmotionalTone, session)
        
        # Check count
        assert emotion_dao.count() >= 6
        
        # Check specific tones
        happy = emotion_dao.find_one_by(name="happy")
        assert happy is not None
        assert "joyful" in happy.positive_examples
        
        sad = emotion_dao.find_one_by(name="sad")
        assert sad is not None
        
        neutral = emotion_dao.find_one_by(name="neutral")
        assert neutral is not None


def test_init_default_agents(empty_test_db):
    """Test initialization of default agents."""
    init_default_agents(empty_test_db)
    
    with empty_test_db.session() as session:
        agent_dao = empty_test_db.get_dao(Agent, session)
        
        # Check count
        assert agent_dao.count() >= 2
        
        # Check specific agents
        default = agent_dao.find_one_by(name="default")
        assert default is not None
        
        assistant = agent_dao.find_one_by(name="assistant")
        assert assistant is not None


def test_initialize_database_complete(empty_test_db):
    """Test complete database initialization."""
    initialize_database(empty_test_db)
    
    with empty_test_db.session() as session:
        # Check all tables have data
        assert empty_test_db.get_dao(EmbeddingType, session).count() > 0
        assert empty_test_db.get_dao(EntityClass, session).count() > 0
        assert empty_test_db.get_dao(LinkageType, session).count() > 0
        assert empty_test_db.get_dao(EmotionalTone, session).count() > 0
        assert empty_test_db.get_dao(Agent, session).count() > 0


def test_idempotent_initialization(empty_test_db):
    """Test that initialization is idempotent."""
    # Initialize once
    initialize_database(empty_test_db)
    
    with empty_test_db.session() as session:
        initial_counts = {
            'embedding': empty_test_db.get_dao(EmbeddingType, session).count(),
            'entity_class': empty_test_db.get_dao(EntityClass, session).count(),
            'linkage': empty_test_db.get_dao(LinkageType, session).count(),
            'emotion': empty_test_db.get_dao(EmotionalTone, session).count(),
            'agent': empty_test_db.get_dao(Agent, session).count()
        }
    
    # Initialize again
    initialize_database(empty_test_db)
    
    with empty_test_db.session() as session:
        # Counts should not change
        assert empty_test_db.get_dao(EmbeddingType, session).count() == initial_counts['embedding']
        assert empty_test_db.get_dao(EntityClass, session).count() == initial_counts['entity_class']
        assert empty_test_db.get_dao(LinkageType, session).count() == initial_counts['linkage']
        assert empty_test_db.get_dao(EmotionalTone, session).count() == initial_counts['emotion']
        assert empty_test_db.get_dao(Agent, session).count() == initial_counts['agent']