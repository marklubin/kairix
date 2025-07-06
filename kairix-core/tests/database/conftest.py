"""
Pytest fixtures for database testing.

This module provides an in-memory SQLite database fixture for fast, isolated tests.
The database is created fresh for each test function and automatically cleaned up.

Usage:
    def test_entity_creation(test_db):
        with test_db.session() as session:
            dao = test_db.get_dao(Entity, session)
            entity = dao.create(name="Test", semantic_id="test_1", entity_class="test")
            assert entity.id is not None
"""
import pytest
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from kairix_core.types.db import Base
from kairix_core.runtime.storage import GenericDAO


@pytest.fixture
def test_db():
    """
    Creates an in-memory SQLite database for testing.
    
    This fixture:
    - Creates a fresh database schema for each test
    - Provides the same interface as StorageRuntime
    - Automatically cleans up after the test
    
    Returns:
        TestStorage: A storage instance backed by in-memory SQLite
    """
    class TestStorage:
        def __init__(self):
            # Use in-memory SQLite
            self.engine = create_engine("sqlite:///:memory:")
            # Create all tables
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
        
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
            """Get vector DAO if available"""
            if not hasattr(self, '_vector_dao'):
                # Try to enable VSS for tests
                try:
                    from kairix_core.runtime.vector_storage import enable_sqlite_vss, create_vss_tables, VectorSearchDAO
                    enable_sqlite_vss(self.engine)
                    create_vss_tables(self.engine)
                    self._vector_dao = VectorSearchDAO(self.engine)
                except:
                    return None
            return self._vector_dao
    
    # Create and return the test storage
    storage = TestStorage()
    yield storage
    # Cleanup happens automatically when SQLite connection closes