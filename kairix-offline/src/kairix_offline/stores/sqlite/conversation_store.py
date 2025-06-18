import os
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
import json
import numpy as np

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .models import (
    Base, Conversation, ConversationFragment, Summary, 
    Embedding, CronJob, ProcessingStatus
)


class ConversationStore:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.environ.get('SQLITE_DB_PATH', 'conversations.db')
        
        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        # SQLite with thread safety for concurrent reads
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
            echo=False
        )
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    @contextmanager
    def session(self):
        """Provide a transactional scope for database operations"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def calculate_checksum(self, content: str) -> str:
        """Calculate SHA256 checksum of content"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def store_conversation(self, file_path: str, content: str, format: str = 'chatgpt') -> Optional[str]:
        """Store a conversation file, returns conversation ID or None if already exists"""
        checksum = self.calculate_checksum(content)
        
        with self.session() as session:
            # Check if already exists
            existing = session.query(Conversation).filter_by(checksum=checksum).first()
            if existing:
                return None
            
            # Create new conversation
            conversation = Conversation(
                file_path=file_path,
                file_name=os.path.basename(file_path),
                content=content,
                format=format,
                checksum=checksum,
                discovered_at=datetime.utcnow()
            )
            
            session.add(conversation)
            session.flush()
            
            return conversation.id
    
    def get_unprocessed_conversations(self, limit: Optional[int] = None) -> List[Conversation]:
        """Get conversations that haven't been processed yet"""
        with self.session() as session:
            query = session.query(Conversation).filter(
                Conversation.processed_at.is_(None)
            ).order_by(Conversation.discovered_at)
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
    
    def mark_conversation_processed(self, conversation_id: str):
        """Mark a conversation as processed"""
        with self.session() as session:
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            if conversation:
                conversation.processed_at = datetime.utcnow()
    
    def store_fragment(self, conversation_id: str, sequence_number: int, 
                      content: str, role: Optional[str] = None,
                      timestamp: Optional[datetime] = None,
                      token_count: Optional[int] = None) -> str:
        """Store a conversation fragment, returns fragment ID"""
        with self.session() as session:
            fragment = ConversationFragment(
                conversation_id=conversation_id,
                sequence_number=sequence_number,
                content=content,
                role=role,
                timestamp=timestamp,
                token_count=token_count
            )
            
            session.add(fragment)
            session.flush()
            
            return fragment.id
    
    def store_summary(self, fragment_id: str, summary_text: str, 
                     model_used: str, token_count: Optional[int] = None) -> str:
        """Store a summary for a fragment, returns summary ID"""
        with self.session() as session:
            summary = Summary(
                fragment_id=fragment_id,
                summary_text=summary_text,
                model_used=model_used,
                token_count=token_count
            )
            
            session.add(summary)
            session.flush()
            
            return summary.id
    
    def store_embedding(self, fragment_id: str, vector: np.ndarray, 
                       model_name: str) -> str:
        """Store an embedding vector for a fragment, returns embedding ID"""
        with self.session() as session:
            embedding = Embedding(
                fragment_id=fragment_id,
                model_name=model_name
            )
            embedding.set_vector(vector)
            
            session.add(embedding)
            session.flush()
            
            return embedding.id
    
    def create_job(self) -> CronJob:
        """Create a new cron job entry"""
        with self.session() as session:
            job = CronJob(
                start_time=datetime.utcnow(),
                status='running'
            )
            
            session.add(job)
            session.flush()
            
            # Make a detached copy with just the ID
            job_copy = CronJob(id=job.id)
            return job_copy
    
    def update_job(self, job_id: str, status: str, 
                  files_found: Optional[int] = None,
                  files_processed: Optional[int] = None,
                  errors_count: Optional[int] = None,
                  error_details: Optional[Dict[str, Any]] = None):
        """Update job status and metrics"""
        with self.session() as session:
            job = session.query(CronJob).filter_by(id=job_id).first()
            if job:
                job.status = status
                if files_found is not None:
                    job.files_found = files_found
                if files_processed is not None:
                    job.files_processed = files_processed
                if errors_count is not None:
                    job.errors_count = errors_count
                if error_details is not None:
                    job.error_details = json.dumps(error_details)
                if status in ['completed', 'failed']:
                    job.end_time = datetime.utcnow()
    
    def create_processing_status(self, conversation_id: str, job_id: str) -> None:
        """Create a processing status entry"""
        with self.session() as session:
            status = ProcessingStatus(
                conversation_id=conversation_id,
                job_id=job_id,
                status='pending'
            )
            
            session.add(status)
            session.flush()
    
    def update_processing_status(self, conversation_id: str, status: str, 
                               stage: Optional[str] = None,
                               error_message: Optional[str] = None):
        """Update processing status for a conversation"""
        with self.session() as session:
            proc_status = session.query(ProcessingStatus).filter_by(
                conversation_id=conversation_id
            ).first()
            
            if proc_status:
                proc_status.status = status
                if stage:
                    proc_status.stage = stage
                if error_message:
                    proc_status.error_message = error_message
                proc_status.updated_at = datetime.utcnow()
    
    def get_job_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent job history"""
        with self.session() as session:
            jobs = session.query(CronJob).order_by(
                CronJob.start_time.desc()
            ).limit(limit).all()
            
            # Convert to dictionaries to avoid session issues
            return [{
                'id': job.id,
                'start_time': job.start_time,
                'end_time': job.end_time,
                'status': job.status,
                'files_found': job.files_found,
                'files_processed': job.files_processed,
                'errors_count': job.errors_count,
                'error_details': job.error_details
            } for job in jobs]
    
    def get_job_details(self, job_id: str) -> Optional[CronJob]:
        """Get detailed information about a specific job"""
        with self.session() as session:
            return session.query(CronJob).filter_by(id=job_id).first()
    
    def get_conversation_by_checksum(self, checksum: str) -> Optional[Conversation]:
        """Get a conversation by its checksum"""
        with self.session() as session:
            return session.query(Conversation).filter_by(checksum=checksum).first()