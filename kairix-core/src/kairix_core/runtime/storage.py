from contextlib import contextmanager
from typing import TypeVar, Generic, Type, List, Optional, Dict, Any
from pathlib import Path

from sqlalchemy.orm.session import Session
from sqlalchemy.orm import sessionmaker

from kairix_core.runtime.logging import LoggingRuntime
from sqlalchemy import create_engine
from kairix_core.types.db import Base
_DEFAULT_DB_FILE = "../.sqlite/kairix.db"

logger = LoggingRuntime().logger

T = TypeVar('T')


class GenericDAO(Generic[T]):
    """Generic Data Access Object for SQLAlchemy models"""
    
    def __init__(self, model_class: Type[T], session: Session):
        self.model_class = model_class
        self.session = session
    
    def get_by_id(self, id: Any) -> Optional[T]:
        """Get a single record by primary key"""
        return self.session.get(self.model_class, id)
    
    def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[T]:
        """Get all records with optional pagination"""
        query = self.session.query(self.model_class)
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def find_by(self, **kwargs: Any) -> List[T]:
        """Find records by field values"""
        return self.session.query(self.model_class).filter_by(**kwargs).all()
    
    def find_one_by(self, **kwargs: Any) -> Optional[T]:
        """Find single record by field values"""
        return self.session.query(self.model_class).filter_by(**kwargs).first()
    
    def create(self, **kwargs: Any) -> T:
        """Create a new record"""
        instance = self.model_class(**kwargs)
        self.session.add(instance)
        self.session.flush()  # Flush to get ID without committing
        return instance
    
    def update(self, instance: T, **kwargs: Any) -> T:
        """Update an existing record"""
        for key, value in kwargs.items():
            setattr(instance, key, value)
        self.session.flush()
        return instance
    
    def delete(self, instance: T) -> None:
        """Delete a record"""
        self.session.delete(instance)
        self.session.flush()
    
    def delete_by_id(self, id: Any) -> bool:
        """Delete by primary key"""
        instance = self.get_by_id(id)
        if instance:
            self.delete(instance)
            return True
        return False
    
    def exists(self, **kwargs: Any) -> bool:
        """Check if record exists"""
        result = self.session.query(
            self.session.query(self.model_class).filter_by(**kwargs).exists()
        ).scalar()
        return bool(result)
    
    def count(self, **kwargs: Any) -> int:
        """Count records matching criteria"""
        return self.session.query(self.model_class).filter_by(**kwargs).count()
    
    def bulk_create(self, objects: List[Dict[str, Any]]) -> List[T]:
        """Create multiple records efficiently"""
        instances = [self.model_class(**obj) for obj in objects]
        self.session.bulk_save_objects(instances, return_defaults=True)
        return instances
class StorageRuntime:

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        # Allow multiple instances with different db_paths
        if 'db_path' in kwargs and kwargs['db_path'] != _DEFAULT_DB_FILE:
            # Create a new instance for custom db_path
            return super().__new__(cls)
        # Use singleton for default db_path
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        # Prevent re-initialization of singleton instance
        if hasattr(self, '_initialized') and self._initialized and db_path is None:
            return
            
        self.db_path = db_path or _DEFAULT_DB_FILE
        
        # Ensure directory exists
        db_dir = Path(self.db_path).parent
        if db_dir != Path(".") and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self._initialized = True
        
        # Initialize vector search (always required)
        from kairix_core.runtime.vector_storage import enable_sqlite_vss, create_vss_tables, VectorSearchDAO
        enable_sqlite_vss(self.engine)
        create_vss_tables(self.engine)
        self._vector_dao = VectorSearchDAO(self.engine)
        logger.info("Vector search enabled")

    @contextmanager
    def session(self):
        session = self.Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_dao(self, model_class: Type[T], session: Session) -> GenericDAO[T]:
        """Get a DAO for a specific model class"""
        return GenericDAO(model_class, session)
    
    @property
    def vector_dao(self):
        """Get the vector search DAO"""
        return self._vector_dao


# Usage example:
# from kairix_core.types.db import Entity, LinkageType
# 
# storage = StorageRuntime()
# 
# with storage.session() as session:
#     # Get DAOs for different models
#     entity_dao = storage.get_dao(Entity, session)
#     linkage_dao = storage.get_dao(LinkageType, session)
#     
#     # Create an entity
#     new_entity = entity_dao.create(
#         semantic_id="entity_123",
#         name="John Doe",
#         entity_class="person"
#     )
#     
#     # Find entities
#     entities = entity_dao.find_by(entity_class="person")
#     
#     # Get by ID
#     entity = entity_dao.get_by_id(1)
#     
#     # Update
#     entity_dao.update(entity, name="Jane Doe")
#     
#     # Check existence
#     exists = entity_dao.exists(semantic_id="entity_123")
