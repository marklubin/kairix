from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import DeclarativeBase, relationship, mapped_column, Mapped
from datetime import datetime

class Base(DeclarativeBase):
    pass


class LinkageType(Base):
    __tablename__ = "linkage_type"
    name: Mapped[str] = mapped_column(String, primary_key=True, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    positive_examples: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_examples: Mapped[str | None] = mapped_column(Text, nullable=True)


class EmotionalTone(Base):
    __tablename__ = "emotional_tone"
    name: Mapped[str] = mapped_column(String, primary_key=True, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    positive_examples: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_examples: Mapped[str | None] = mapped_column(Text, nullable=True)


class EntityClass(Base):
    __tablename__ = "entity_class"
    name: Mapped[str] = mapped_column(String, primary_key=True, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    positive_examples: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_examples: Mapped[str | None] = mapped_column(Text, nullable=True)


class EmbeddingType(Base):
    __tablename__ = "embedding_type"
    name: Mapped[str] = mapped_column(String, primary_key=True, unique=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    vector_length: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class LinkageObservation(Base):
    __tablename__ = "linkage_observations"
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    target_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    linkage_type = Column(String, ForeignKey('linkage_type.name'), nullable=False)
    
    approximate_occurrence = Column(DateTime, default=datetime.utcnow)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    source_descriptor = Column(String)
    emotional_tone = Column(String, ForeignKey('emotional_tone.name'), nullable=True)



# Association table for Entity <-> Entity relationships (SemanticLinkage)
class SemanticLinkage(Base):
    __tablename__ = 'semantic_linkages'

    source_id = Column(Integer, ForeignKey('entities.id'), primary_key=True)
    target_id = Column(Integer, ForeignKey('entities.id'), primary_key=True)
    linkage_type = Column(String, ForeignKey('linkage_type.name'), primary_key=True)
    weight = Column(Integer, default=1)
    first_noticed_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Entity", foreign_keys=[source_id], back_populates="outgoing_links")
    target = relationship("Entity", foreign_keys=[target_id], back_populates="incoming_links")
    linkage_type_ref = relationship("LinkageType")


class Entity(Base):
    __tablename__ = 'entities'

    id = Column(Integer, primary_key=True)
    semantic_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    entity_class = Column(String, ForeignKey('entity_class.name'), nullable=False)
    embedding_type = Column(String, ForeignKey('embedding_type.name'), nullable=True)
    embedding = Column(JSON, nullable=True)  # vector stored as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    outgoing_links = relationship("SemanticLinkage", foreign_keys=[SemanticLinkage.source_id], back_populates="source")
    incoming_links = relationship("SemanticLinkage", foreign_keys=[SemanticLinkage.target_id], back_populates="target")
    entity_class_ref = relationship("EntityClass")
    embedding_type_ref = relationship("EmbeddingType")
    observations = relationship("EntityObservation", back_populates="entity")


class EntityObservation(Base):
    __tablename__ = 'entity_observations'
    
    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    observation_type = Column(String, nullable=False)
    observation_value = Column(Text)
    approximate_occurrence = Column(DateTime, default=datetime.utcnow)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    source_descriptor = Column(String)
    emotional_tone = Column(String, ForeignKey('emotional_tone.name'), nullable=True)
    
    entity = relationship("Entity")


class Agent(Base):
    __tablename__ = 'agents'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)



class Source(Base):
    __tablename__ = 'sources'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    source_type = Column(String, nullable=False)  # filesystem, website, sensor, etc.
    format = Column(String, nullable=False)  # pdf, txt, html, json, etc.
    processing_class = Column(String, nullable=False)  # name of the processing job/class
    configuration = Column(Text)  # JSON-like config but stored as text
    created_at = Column(DateTime, default=datetime.utcnow)
    
    objects = relationship("SourceObject", back_populates="source")


class SourceObject(Base):
    __tablename__ = 'source_objects'
    
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('sources.id'), nullable=False)
    object_path = Column(String, nullable=False)  # file path, URL, or other identifier
    content = Column(Text, nullable=True)  # actual content if stored in DB
    content_hash = Column(String)  # for deduplication
    extra_data = Column(Text)  # JSON-like metadata stored as text
    ingested_at = Column(DateTime, default=datetime.utcnow)
    
    source = relationship("Source", back_populates="objects")

class Summary(Base):
    __tablename__ = 'summaries'
    
    id = Column(Integer, primary_key=True)
    uid = Column(String, unique=True, nullable=True)  # For idempotency from Neo4j
    summary_text = Column(Text, nullable=False)
    extractions_performed = Column(JSON, nullable=True, default=list)  # Array of extraction types
    approximate_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    memory_shards = relationship("MemoryShard", back_populates="summary")


class MemoryShard(Base):
    __tablename__ = 'memory_shards'
    
    id = Column(Integer, primary_key=True)
    uid = Column(String, unique=True, nullable=True)  # For idempotency from Neo4j
    contents = Column(Text, nullable=False)
    embedding_type = Column(String, ForeignKey('embedding_type.name'), nullable=False)
    embedding = Column(JSON, nullable=False)  # vector stored as JSON
    created_at = Column(DateTime, default=datetime.utcnow)

    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=False)
    source_object_id = Column(Integer, ForeignKey('source_objects.id'), nullable=True)
    summary_id = Column(Integer, ForeignKey('summaries.id'), nullable=True)

    agent = relationship("Agent")
    source_object = relationship("SourceObject")
    embedding_type_ref = relationship("EmbeddingType")
    summary = relationship("Summary", back_populates="memory_shards")


class Notebook(Base):
    __tablename__ = 'notebooks'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=False, unique=True)  # One per agent
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    agent = relationship("Agent", backref="notebook")
    notes = relationship("Note", back_populates="notebook", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = 'notes'
    
    id = Column(Integer, primary_key=True)
    notebook_id = Column(Integer, ForeignKey('notebooks.id'), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    notebook = relationship("Notebook", back_populates="notes")


class ConversationMessage(Base):
    __tablename__ = 'conversation_messages'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=False)
    user_id = Column(String, nullable=False)  # External user identifier
    thread_id = Column(String, nullable=False)  # Internal thread grouping
    sequence_number = Column(Integer, nullable=False)  # Sequential within thread
    
    role = Column(String, nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    extra_data = Column(Text)  # JSON-like metadata
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    agent = relationship("Agent")
    
    # Ensure sequence integrity within a thread
    __table_args__ = (
        # Unique constraint on thread + sequence to prevent gaps/duplicates
        UniqueConstraint('thread_id', 'sequence_number', name='_thread_sequence_uc'),
        # Index for efficient queries
        Index('idx_thread_sequence', 'thread_id', 'sequence_number'),
        Index('idx_agent_user', 'agent_id', 'user_id'),
    )
