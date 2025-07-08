#!/usr/bin/env python3
"""Direct Neo4j to SQLite migration script with custom database path."""
import sys
import logging
import traceback
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_neo4j_to_custom_sqlite(neo4j_url: str, sqlite_path: str):
    """
    Migrate Neo4j data to a custom SQLite database file.
    
    Args:
        neo4j_url: Neo4j connection URL (e.g., bolt://neo4j:password@localhost:7687)
        sqlite_path: Path to the SQLite database file
    """
    try:
        # Create SQLite engine
        engine = create_engine(f"sqlite:///{sqlite_path}")
        
        # Import models to create tables
        from kairix_core.types.db import Base
        Base.metadata.create_all(engine)
        
        # Create a mock StorageRuntime that uses our custom engine
        class CustomStorageRuntime:
            def __init__(self, engine):
                self.engine = engine
                self.Session = sessionmaker(bind=engine)
                self._vector_dao = None  # No vector search for now
                
            @property
            def vector_dao(self):
                return self._vector_dao
                
            def session(self):
                from contextlib import contextmanager
                
                @contextmanager
                def _session():
                    session = self.Session()
                    try:
                        yield session
                        session.commit()
                    except:
                        session.rollback()
                        raise
                    finally:
                        session.close()
                
                return _session()
                
            def get_dao(self, model_class, session):
                from kairix_core.runtime.storage import GenericDAO
                return GenericDAO(model_class, session)
        
        # Create custom storage runtime
        storage = CustomStorageRuntime(engine)
        
        # Import converter
        from kairix_core.database.neo4j_to_sqlite import Neo4jToSQLiteConverter
        
        # Create converter with our custom storage
        converter = Neo4jToSQLiteConverter(neo4j_url, storage)
        
        # Run conversion
        logger.info(f"Starting migration from {neo4j_url} to {sqlite_path}")
        converter.convert_all()
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        traceback.print_exc()
        return False
    
    return True


def main():
    if len(sys.argv) < 3:
        print("Usage: python migrate_neo4j_direct.py <neo4j_url> <sqlite_path>")
        print("Example: python migrate_neo4j_direct.py bolt://neo4j:password@localhost:7687 mydata.db")
        sys.exit(1)
    
    neo4j_url = sys.argv[1]
    sqlite_path = sys.argv[2]
    
    success = migrate_neo4j_to_custom_sqlite(neo4j_url, sqlite_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()