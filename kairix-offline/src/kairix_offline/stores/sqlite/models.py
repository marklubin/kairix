import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, LargeBinary, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import numpy as np

Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Conversation(Base):
    __tablename__ = 'conversations'
    
    id = Column(String, primary_key=True, default=generate_uuid)
    file_path = Column(Text, nullable=False)
    file_name = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    format = Column(Text, nullable=False)
    checksum = Column(Text, nullable=False, unique=True, index=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    fragments = relationship("ConversationFragment", back_populates="conversation", cascade="all, delete-orphan")
    processing_status = relationship("ProcessingStatus", back_populates="conversation", uselist=False)


class ConversationFragment(Base):
    __tablename__ = 'conversation_fragments'
    
    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey('conversations.id'), nullable=False, index=True)
    sequence_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    role = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="fragments")
    summary = relationship("Summary", back_populates="fragment", uselist=False)
    embedding = relationship("Embedding", back_populates="fragment", uselist=False)


class Summary(Base):
    __tablename__ = 'summaries'
    
    id = Column(String, primary_key=True, default=generate_uuid)
    fragment_id = Column(String, ForeignKey('conversation_fragments.id'), nullable=False, unique=True, index=True)
    summary_text = Column(Text, nullable=False)
    model_used = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    fragment = relationship("ConversationFragment", back_populates="summary")


class Embedding(Base):
    __tablename__ = 'embeddings'
    
    id = Column(String, primary_key=True, default=generate_uuid)
    fragment_id = Column(String, ForeignKey('conversation_fragments.id'), nullable=False, unique=True, index=True)
    embedding_vector = Column(LargeBinary, nullable=False)
    model_name = Column(Text, nullable=False)
    dimensions = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    fragment = relationship("ConversationFragment", back_populates="embedding")
    
    def set_vector(self, vector: np.ndarray):
        """Pack numpy array as bytes for efficient storage"""
        self.embedding_vector = vector.astype(np.float32).tobytes()
        self.dimensions = len(vector)
    
    def get_vector(self) -> np.ndarray:
        """Unpack bytes to numpy array"""
        return np.frombuffer(self.embedding_vector, dtype=np.float32)


class CronJob(Base):
    __tablename__ = 'cron_jobs'
    
    id = Column(String, primary_key=True, default=generate_uuid)
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    end_time = Column(DateTime, nullable=True)
    status = Column(Text, nullable=False, default='running')
    files_found = Column(Integer, default=0)
    files_processed = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    error_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    processing_statuses = relationship("ProcessingStatus", back_populates="job")


class ProcessingStatus(Base):
    __tablename__ = 'processing_status'
    
    conversation_id = Column(String, ForeignKey('conversations.id'), primary_key=True)
    job_id = Column(String, ForeignKey('cron_jobs.id'), nullable=False)
    status = Column(Text, nullable=False, default='pending')
    stage = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    
    conversation = relationship("Conversation", back_populates="processing_status")
    job = relationship("CronJob", back_populates="processing_statuses")