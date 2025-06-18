#!/usr/bin/env python3
"""
Cron job script for ingesting conversation data with dual storage (SQLite + Neo4j)
Runs daily to process new conversation files from the configured directory.
"""

import os
import sys
import json
import glob
import traceback
import subprocess
from datetime import datetime
from typing import List
import hashlib

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv(verbose=True)

from kairix_core.util.environment import get_or_raise  # noqa: E402
from kairix_core.types import MemoryShard, Summary, Embedding, SourceDocument  # noqa: E402
from kairix_offline.processing import initialize_processing  # noqa: E402
from kairix_offline.stores.sqlite import ConversationStore  # noqa: E402


class ConversationIngestionJob:
    """Handles daily ingestion of conversation files with dual storage"""
    
    def __init__(self):
        # Initialize stores
        self.sqlite_store = ConversationStore()
        
        # Get configuration from environment
        self.chat_logs_path = get_or_raise("CHAT_LOGS_PATH")
        self.enabled = os.environ.get("CRON_ENABLED", "true").lower() == "true"
        
        # Initialize processing components
        initialize_processing()
        
        # Get the synthesizer from the module
        from kairix_offline.processing import summary_memory_synthezier
        self.synth = summary_memory_synthezier
        
        # Track errors for system broadcast
        self.neo4j_errors = []
    
    def broadcast_system_message(self, message: str):
        """Broadcast a system message to all users on the host"""
        try:
            # Using wall command to broadcast to all logged-in users
            subprocess.run(
                ['wall', f"[Kairix Cron Error] {message}"],
                capture_output=True,
                text=True,
                check=False
            )
            
            # Also log to syslog
            subprocess.run(
                ['logger', '-t', 'kairix-cron', f"ERROR: {message}"],
                capture_output=True,
                text=True,
                check=False
            )
        except Exception as e:
            print(f"Failed to broadcast message: {e}")
    
    def scan_for_files(self) -> List[str]:
        """Scan the configured directory for conversation files"""
        if not os.path.exists(self.chat_logs_path):
            print(f"Chat logs directory does not exist: {self.chat_logs_path}")
            return []
        
        # Support multiple file patterns
        patterns = ['*.json', '*.txt', '*.log']
        files = []
        
        for pattern in patterns:
            path_pattern = os.path.join(self.chat_logs_path, pattern)
            files.extend(glob.glob(path_pattern))
        
        return sorted(files)
    
    def process_file(self, file_path: str, job_id: str) -> bool:
        """Process a single conversation file through the pipeline"""
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Calculate checksum
            checksum = self.sqlite_store.calculate_checksum(content)
            
            # Check if already processed
            existing = self.sqlite_store.get_conversation_by_checksum(checksum)
            if existing:
                print(f"File already processed: {file_path}")
                return True
            
            # Store in SQLite
            conversation_id = self.sqlite_store.store_conversation(
                file_path=file_path,
                content=content,
                format='chatgpt'  # TODO: Detect format from file
            )
            
            if not conversation_id:
                print(f"Failed to store conversation: {file_path}")
                return False
            
            # Create processing status
            self.sqlite_store.create_processing_status(conversation_id, job_id)
            
            # Update status to processing
            self.sqlite_store.update_processing_status(
                conversation_id, 'processing', stage='parsing'
            )
            
            # Parse conversation data (assuming JSON format)
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # If not JSON, treat as plain text
                data = {'messages': [{'role': 'user', 'content': content}]}
            
            # Process through pipeline stages
            fragment_count = 0
            
            # 1. Chunk the conversation
            self.sqlite_store.update_processing_status(
                conversation_id, 'processing', stage='chunking'
            )
            
            # For now, simple chunking by message
            messages = data.get('messages', [])
            for idx, message in enumerate(messages):
                fragment_id = self.sqlite_store.store_fragment(
                    conversation_id=conversation_id,
                    sequence_number=idx,
                    content=message.get('content', ''),
                    role=message.get('role'),
                    timestamp=None,  # TODO: Parse timestamps
                    token_count=len(message.get('content', '').split())
                )
                fragment_count += 1
                
                # 2. Generate summary
                self.sqlite_store.update_processing_status(
                    conversation_id, 'processing', stage=f'summarizing_{idx}'
                )
                
                summary_text = self.synth.inference_provider.predict(
                    message.get('content', ''),
                    self.synth.inference_parameters
                )
                self.sqlite_store.store_summary(
                    fragment_id=fragment_id,
                    summary_text=summary_text,
                    model_used=get_or_raise("KAIRIX_SUMMARIZER_MODEL")
                )
                
                # 3. Generate embedding
                self.sqlite_store.update_processing_status(
                    conversation_id, 'processing', stage=f'embedding_{idx}'
                )
                
                embedding_vector = self.synth.embedder.encode([message.get('content', '')])[0]
                self.sqlite_store.store_embedding(
                    fragment_id=fragment_id,
                    vector=embedding_vector,
                    model_name=get_or_raise("KAIRIX_EMBEDDER_MODEL")
                )
                
                # 4. Store in Neo4j (dual storage)
                try:
                    self.sqlite_store.update_processing_status(
                        conversation_id, 'processing', stage=f'neo4j_sync_{idx}'
                    )
                    
                    # Create unique ID for Neo4j entities
                    idempotency_key = hashlib.sha256(
                        f"{conversation_id}_{fragment_id}".encode()
                    ).hexdigest()
                    
                    # Store as SourceDocument first
                    source_doc = SourceDocument.get_or_none(idempotency_key)
                    if not source_doc:
                        source_doc = SourceDocument(
                            uid=idempotency_key,
                            label=f"conversation:{conversation_id}:fragment:{idx}",
                            content=message.get('content', ''),
                            content_type='conversation'
                        )
                        source_doc.save()
                    
                    # Create Summary in Neo4j
                    neo4j_summary = Summary.get_or_none(f"summary_{idempotency_key}")
                    if not neo4j_summary:
                        neo4j_summary = Summary(
                            uid=f"summary_{idempotency_key}",
                            summary_text=summary_text
                        )
                        neo4j_summary.save()
                    
                    # Create Embedding in Neo4j
                    neo4j_embedding = Embedding.get_or_none(f"embedding_{idempotency_key}")
                    if not neo4j_embedding:
                        neo4j_embedding = Embedding(
                            uid=f"embedding_{idempotency_key}",
                            embedding_model=get_or_raise("KAIRIX_EMBEDDER_MODEL"),
                            vector=embedding_vector.tolist()
                        )
                        neo4j_embedding.save()
                    
                    # Create MemoryShard and connect relationships
                    memory_shard = MemoryShard.get_or_none(f"shard_{idempotency_key}")
                    if not memory_shard:
                        memory_shard = MemoryShard(
                            uid=f"shard_{idempotency_key}",
                            shard_contents=summary_text,
                            vector_address=embedding_vector.tolist()
                        )
                        memory_shard.save()
                        
                        # Connect relationships
                        memory_shard.embedding.connect(neo4j_embedding)
                        memory_shard.summary.connect(neo4j_summary)
                        memory_shard.source_document.connect(source_doc)
                except Exception as e:
                    # Track Neo4j errors but don't fail the whole process
                    error_msg = f"Neo4j storage failed for {file_path}: {str(e)}"
                    self.neo4j_errors.append(error_msg)
                    print(error_msg)
            
            # Mark conversation as processed
            self.sqlite_store.mark_conversation_processed(conversation_id)
            self.sqlite_store.update_processing_status(
                conversation_id, 'completed', stage='done'
            )
            
            print(f"Successfully processed {file_path} ({fragment_count} fragments)")
            return True
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            
            # Update status to failed
            if 'conversation_id' in locals() and conversation_id:
                self.sqlite_store.update_processing_status(
                    conversation_id, 'failed', error_message=str(e)
                )
            
            return False
    
    def run(self):
        """Main entry point for the cron job"""
        if not self.enabled:
            print("Cron job is disabled. Set CRON_ENABLED=true to enable.")
            return
        
        print(f"Starting conversation ingestion job at {datetime.utcnow()}")
        
        # Create job entry and store the ID
        job = self.sqlite_store.create_job()
        job_id = job.id  # Store the ID before the session closes
        
        try:
            # Scan for files
            files = self.scan_for_files()
            print(f"Found {len(files)} files to process")
            
            self.sqlite_store.update_job(
                job_id, 
                status='running',
                files_found=len(files)
            )
            
            # Process each file
            processed_count = 0
            error_count = 0
            
            for file_path in files:
                print(f"Processing: {file_path}")
                if self.process_file(file_path, job_id):
                    processed_count += 1
                else:
                    error_count += 1
                
                # Update job progress
                self.sqlite_store.update_job(
                    job_id,
                    status='running',
                    files_processed=processed_count,
                    errors_count=error_count
                )
            
            # Finalize job
            final_status = 'completed' if error_count == 0 else 'completed_with_errors'
            self.sqlite_store.update_job(
                job_id,
                status=final_status,
                files_processed=processed_count,
                errors_count=error_count,
                error_details={'neo4j_errors': self.neo4j_errors} if self.neo4j_errors else None
            )
            
            # Broadcast Neo4j errors if any
            if self.neo4j_errors:
                error_summary = f"Neo4j storage failed for {len(self.neo4j_errors)} operations. Check logs for details."
                self.broadcast_system_message(error_summary)
            
            print(f"Job completed: {processed_count} processed, {error_count} errors")
            
        except Exception as e:
            error_msg = f"Job failed: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            
            self.sqlite_store.update_job(
                job_id,
                status='failed',
                error_details={'error': str(e), 'traceback': traceback.format_exc()}
            )
            
            # Broadcast critical failure
            self.broadcast_system_message(f"Conversation ingestion job failed: {str(e)}")


def main():
    """Main entry point"""
    try:
        job = ConversationIngestionJob()
        job.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()