"""Integration test for conversation ingestion cron job with SQLite and Neo4j"""

import json
import os
import tempfile
from datetime import datetime
from unittest.mock import patch

import pytest
from testcontainers.neo4j import Neo4jContainer

from kairix_offline.stores.sqlite import ConversationStore
from scripts.conversation_ingestion_cron import ConversationIngestionJob


@pytest.fixture
def neo4j_container():
    """Provide a Neo4j test container"""
    with Neo4jContainer("neo4j:5.13.0") as neo4j:
        yield neo4j


@pytest.fixture 
def temp_dirs():
    """Create temporary directories for test data"""
    with tempfile.TemporaryDirectory() as temp_dir:
        chat_logs_dir = os.path.join(temp_dir, "chat_logs")
        os.makedirs(chat_logs_dir, exist_ok=True)
        
        db_path = os.path.join(temp_dir, "test_conversations.db")
        
        yield {
            'temp_dir': temp_dir,
            'chat_logs_dir': chat_logs_dir,
            'db_path': db_path
        }


@pytest.fixture
def sample_conversations(temp_dirs):
    """Create sample conversation files"""
    conversations = [
        {
            "id": "test_conv_1",
            "messages": [
                {"role": "user", "content": "What is machine learning?"},
                {"role": "assistant", "content": "Machine learning is a subset of artificial intelligence that enables systems to learn from data."}
            ],
            "timestamp": datetime.now().isoformat()
        },
        {
            "id": "test_conv_2", 
            "messages": [
                {"role": "user", "content": "How do neural networks work?"},
                {"role": "assistant", "content": "Neural networks are computing systems inspired by biological neural networks."},
                {"role": "user", "content": "What are the main types?"},
                {"role": "assistant", "content": "The main types include feedforward, convolutional, and recurrent neural networks."}
            ],
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    file_paths = []
    for i, conv in enumerate(conversations):
        file_path = os.path.join(temp_dirs['chat_logs_dir'], f"test_conversation_{i+1}.json")
        with open(file_path, 'w') as f:
            json.dump(conv, f, indent=2)
        file_paths.append(file_path)
    
    return file_paths


@pytest.mark.integration
def test_conversation_ingestion_end_to_end(neo4j_container, temp_dirs, sample_conversations):
    """Test the complete conversation ingestion pipeline"""
    
    # Set up environment variables
    env_vars = {
        'NEO4J_URL': neo4j_container.get_connection_url(),
        'SQLITE_DB_PATH': temp_dirs['db_path'],
        'CHAT_LOGS_PATH': temp_dirs['chat_logs_dir'],
        'CRON_ENABLED': 'true',
        'KAIRIX_INFERENCE_PROVIDER': 'mock',
        'KAIRIX_SUMMARIZER_MODEL': 'mock-model',
        'KAIRIX_EMBEDDER_MODEL': 'mock-embedder',
        'KAIRIX_CHUNK_SIZE': '1000',
        'KAIRIX_EMBEDDER_DEVICE': 'cpu',
        'KAIRIX_EMBEDDING_BATCH_SIZE': '1',
        'KAIRIX_SUMMARIZER_MAX_TOKENS': '100',
        'KAIRIX_SUMMARIZER_TEMPERATURE': '0.5'
    }
    
    with patch.dict(os.environ, env_vars):
        # Mock the inference provider and embedder
        with patch('kairix_offline.processing.get_inference_provider_for_environement') as mock_provider:
            with patch('transformers.AutoTokenizer.from_pretrained') as mock_tokenizer:
                with patch('sentence_transformers.SentenceTransformer') as mock_embedder:
                    # Set up tokenizer mock
                    mock_tokenizer_instance = mock_tokenizer.return_value
                    mock_tokenizer_instance.model_max_length = 512
                    
                    # Set up mocks
                    mock_inference = mock_provider.return_value
                    mock_inference.predict.return_value = "This is a summary of the content."
                    
                    mock_embed_instance = mock_embedder.return_value
                    mock_embed_instance.encode.return_value = [[0.1] * 768]  # 768-dim vector
                    mock_embed_instance.model_card_data.base_model = "mock-embedder"
                    
                    # Initialize and run the job
                    job = ConversationIngestionJob()
                    job.run()
        
        # Verify SQLite storage
        sqlite_store = ConversationStore(temp_dirs['db_path'])
        
        # Check job was created and completed
        jobs = sqlite_store.get_job_history(limit=1)
        assert len(jobs) == 1
        assert jobs[0].status == 'completed'
        assert jobs[0].files_found == 2
        assert jobs[0].files_processed == 2
        assert jobs[0].errors_count == 0
        
        # Check conversations were stored
        with sqlite_store.session() as session:
            from kairix_offline.stores.sqlite.models import Conversation, ConversationFragment, Summary, Embedding
            
            conversations = session.query(Conversation).all()
            assert len(conversations) == 2
            
            # Check fragments
            fragments = session.query(ConversationFragment).all()
            assert len(fragments) == 6  # 2 + 4 messages total
            
            # Check summaries
            summaries = session.query(Summary).all()
            assert len(summaries) == 6
            assert all(s.summary_text == "This is a summary of the content." for s in summaries)
            
            # Check embeddings
            embeddings = session.query(Embedding).all()
            assert len(embeddings) == 6
            assert all(e.dimensions == 768 for e in embeddings)


@pytest.mark.integration
def test_idempotent_processing(neo4j_container, temp_dirs, sample_conversations):
    """Test that files are not reprocessed on subsequent runs"""
    
    env_vars = {
        'NEO4J_URL': neo4j_container.get_connection_url(),
        'SQLITE_DB_PATH': temp_dirs['db_path'],
        'CHAT_LOGS_PATH': temp_dirs['chat_logs_dir'],
        'CRON_ENABLED': 'true',
        'KAIRIX_INFERENCE_PROVIDER': 'mock',
        'KAIRIX_SUMMARIZER_MODEL': 'mock-model',
        'KAIRIX_EMBEDDER_MODEL': 'mock-embedder',
        'KAIRIX_CHUNK_SIZE': '1000',
        'KAIRIX_EMBEDDER_DEVICE': 'cpu',
        'KAIRIX_EMBEDDING_BATCH_SIZE': '1',
        'KAIRIX_SUMMARIZER_MAX_TOKENS': '100',
        'KAIRIX_SUMMARIZER_TEMPERATURE': '0.5'
    }
    
    with patch.dict(os.environ, env_vars):
        with patch('kairix_offline.processing.get_inference_provider_for_environement') as mock_provider:
            with patch('transformers.AutoTokenizer.from_pretrained') as mock_tokenizer:
                with patch('sentence_transformers.SentenceTransformer') as mock_embedder:
                    # Set up tokenizer mock
                    mock_tokenizer_instance = mock_tokenizer.return_value
                    mock_tokenizer_instance.model_max_length = 512
                    
                    # Set up mocks
                    mock_inference = mock_provider.return_value
                    mock_inference.predict.return_value = "Summary"
                    
                    mock_embed_instance = mock_embedder.return_value
                    mock_embed_instance.encode.return_value = [[0.1] * 768]
                    mock_embed_instance.model_card_data.base_model = "mock-embedder"
                    
                    # Run job twice
                    job1 = ConversationIngestionJob()
                    job1.run()
                    
                    job2 = ConversationIngestionJob()
                    job2.run()
        
        # Verify no duplicates
        sqlite_store = ConversationStore(temp_dirs['db_path'])
        
        jobs = sqlite_store.get_job_history(limit=2)
        assert len(jobs) == 2
        
        # First job should process files
        assert jobs[1].files_processed == 2
        
        # Second job should find files but not reprocess
        assert jobs[0].files_processed == 2  # Both marked as processed due to checksum
        
        # Check no duplicate data
        with sqlite_store.session() as session:
            from kairix_offline.stores.sqlite.models import Conversation
            conversations = session.query(Conversation).all()
            assert len(conversations) == 2  # No duplicates


@pytest.mark.integration  
def test_neo4j_failure_handling(neo4j_container, temp_dirs, sample_conversations):
    """Test that Neo4j failures don't stop SQLite storage"""
    
    env_vars = {
        'NEO4J_URL': 'bolt://invalid:7687',  # Invalid Neo4j URL
        'SQLITE_DB_PATH': temp_dirs['db_path'],
        'CHAT_LOGS_PATH': temp_dirs['chat_logs_dir'],
        'CRON_ENABLED': 'true',
        'KAIRIX_INFERENCE_PROVIDER': 'mock',
        'KAIRIX_SUMMARIZER_MODEL': 'mock-model',
        'KAIRIX_EMBEDDER_MODEL': 'mock-embedder',
        'KAIRIX_CHUNK_SIZE': '1000',
        'KAIRIX_EMBEDDER_DEVICE': 'cpu',
        'KAIRIX_EMBEDDING_BATCH_SIZE': '1',
        'KAIRIX_SUMMARIZER_MAX_TOKENS': '100',
        'KAIRIX_SUMMARIZER_TEMPERATURE': '0.5'
    }
    
    with patch.dict(os.environ, env_vars):
        with patch('kairix_offline.processing.get_inference_provider_for_environement') as mock_provider:
            with patch('transformers.AutoTokenizer.from_pretrained') as mock_tokenizer:
                with patch('sentence_transformers.SentenceTransformer') as mock_embedder:
                    with patch('neomodel.db.install_all_labels'):  # Skip Neo4j setup
                        # Set up tokenizer mock
                        mock_tokenizer_instance = mock_tokenizer.return_value
                        mock_tokenizer_instance.model_max_length = 512
                        
                        # Set up mocks
                        mock_inference = mock_provider.return_value
                        mock_inference.predict.return_value = "Summary"
                        
                        mock_embed_instance = mock_embedder.return_value
                        mock_embed_instance.encode.return_value = [[0.1] * 768]
                        mock_embed_instance.model_card_data.base_model = "mock-embedder"
                        
                        # Run job - Neo4j will fail but SQLite should succeed
                        job = ConversationIngestionJob()
                        job.run()
        
        # Verify SQLite data was stored despite Neo4j failures
        sqlite_store = ConversationStore(temp_dirs['db_path'])
        
        jobs = sqlite_store.get_job_history(limit=1)
        assert len(jobs) == 1
        assert jobs[0].status in ['completed', 'completed_with_errors']
        
        # Check that SQLite data was stored
        with sqlite_store.session() as session:
            from kairix_offline.stores.sqlite.models import ConversationFragment
            fragments = session.query(ConversationFragment).all()
            assert len(fragments) == 6  # All fragments stored despite Neo4j errors