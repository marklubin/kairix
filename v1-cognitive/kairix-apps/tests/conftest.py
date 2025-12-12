"""Common test fixtures and configuration for kairix-engine tests."""

from contextlib import contextmanager
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load test environment variables before importing any modules
env_file = Path(__file__).parent.parent / ".env.test"
if env_file.exists():
    load_dotenv(env_file, override=True)

from kairix_core.runtime.storage import GenericDAO  # noqa: E402
from kairix_core.runtime.vector_storage import VectorSearchDAO, create_vss_tables, enable_sqlite_vss  # noqa: E402
from kairix_core.types.db import Base  # noqa: E402


@pytest.fixture
def test_db():
    """Creates an in-memory SQLite database for testing."""
    class TestStorage:
        def __init__(self):
            # Use in-memory SQLite
            self.engine = create_engine("sqlite:///:memory:")
            # Create all tables
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            
            # Initialize vector search
            enable_sqlite_vss(self.engine)
            create_vss_tables(self.engine)
            self._vector_dao = VectorSearchDAO(self.engine)
        
        @contextmanager
        def session(self):
            """Context manager for database sessions"""
            session = self.Session()
            try:
                yield session
                session.commit()
            except:
                session.rollback()
                raise
            finally:
                session.close()
        
        def get_dao(self, model_class, session):
            """Get a DAO for a specific model"""
            return GenericDAO(model_class, session)
        
        @property
        def vector_dao(self):
            """Get vector DAO"""
            return self._vector_dao
    
    # Create and return the test storage
    storage = TestStorage()
    
    # Initialize default data
    from kairix_core.database.init_data import initialize_database
    initialize_database(storage)
    
    # Get default agent ID for tests
    from kairix_core.types.db import Agent
    with storage.session() as session:
        agent_dao = storage.get_dao(Agent, session)
        default_agent = agent_dao.find_one_by(name="default")
        storage.default_agent_id = default_agent.id if default_agent else 1
    
    return storage


@pytest.fixture
def test_embedding_model() -> str:
    """Fixture providing a test embedding model name."""
    return "sentence-transformers/all-MiniLM-L6-v2"  # Smaller model for tests