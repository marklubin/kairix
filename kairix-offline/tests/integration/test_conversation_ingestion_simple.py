"""Simplified integration test for conversation ingestion"""

import json
import os
import tempfile

import pytest
import numpy as np

from kairix_offline.stores.sqlite import ConversationStore


@pytest.mark.integration
def test_sqlite_conversation_storage():
    """Test basic SQLite storage functionality"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_conversations.db")
        store = ConversationStore(db_path)
        
        # Test storing a conversation
        content = json.dumps({
            "id": "test_1",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
        })
        
        # Store conversation
        conv_id = store.store_conversation(
            file_path="/test/conv1.json",
            content=content,
            format="chatgpt"
        )
        
        assert conv_id is not None
        
        # Test idempotency - same content should return None
        conv_id2 = store.store_conversation(
            file_path="/test/conv1_copy.json",  # Different path
            content=content,  # Same content
            format="chatgpt"
        )
        
        assert conv_id2 is None  # Should not create duplicate
        
        # Store fragments
        frag1_id = store.store_fragment(
            conversation_id=conv_id,
            sequence_number=0,
            content="Hello",
            role="user"
        )
        
        frag2_id = store.store_fragment(
            conversation_id=conv_id,
            sequence_number=1,
            content="Hi there!",
            role="assistant"
        )
        
        assert frag1_id is not None
        assert frag2_id is not None
        
        # Store summaries
        sum1_id = store.store_summary(
            fragment_id=frag1_id,
            summary_text="User greeting",
            model_used="test-model"
        )
        
        assert sum1_id is not None
        
        # Store embeddings
        embedding = np.random.rand(768)
        
        emb1_id = store.store_embedding(
            fragment_id=frag1_id,
            vector=embedding,
            model_name="test-embedder"
        )
        
        assert emb1_id is not None
        
        # Test job tracking
        job = store.create_job()
        assert job.id is not None
        
        store.update_job(
            job.id,
            status='completed',
            files_found=1,
            files_processed=1,
            errors_count=0
        )
        
        # Verify job history
        jobs = store.get_job_history(limit=1)
        assert len(jobs) == 1
        assert jobs[0]['status'] == 'completed'
        assert jobs[0]['files_processed'] == 1


@pytest.mark.integration
def test_end_to_end_flow_without_ml():
    """Test the complete flow without ML models"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test data
        chat_logs_dir = os.path.join(temp_dir, "chat_logs")
        os.makedirs(chat_logs_dir)
        
        conv_data = {
            "id": "test_conv",
            "messages": [
                {"role": "user", "content": "What is Python?"},
                {"role": "assistant", "content": "Python is a programming language."},
                {"role": "user", "content": "Thanks!"},
                {"role": "assistant", "content": "You're welcome!"}
            ]
        }
        
        conv_file = os.path.join(chat_logs_dir, "test_conversation.json")
        with open(conv_file, 'w') as f:
            json.dump(conv_data, f)
        
        # Initialize store
        db_path = os.path.join(temp_dir, "conversations.db")
        store = ConversationStore(db_path)
        
        # Simulate the cron job workflow
        job = store.create_job()
        job_id = job.id
        
        # Read and store conversation
        with open(conv_file, 'r') as f:
            content = f.read()
        
        conv_id = store.store_conversation(
            file_path=conv_file,
            content=content,
            format="chatgpt"
        )
        
        # Process messages
        messages = conv_data["messages"]
        for idx, msg in enumerate(messages):
            # Store fragment
            frag_id = store.store_fragment(
                conversation_id=conv_id,
                sequence_number=idx,
                content=msg["content"],
                role=msg["role"]
            )
            
            # Store mock summary
            store.store_summary(
                fragment_id=frag_id,
                summary_text=f"Summary of: {msg['content'][:20]}...",
                model_used="mock-model"
            )
            
            # Store mock embedding
            mock_embedding = np.ones(768) * 0.1
            store.store_embedding(
                fragment_id=frag_id,
                vector=mock_embedding,
                model_name="mock-embedder"
            )
        
        # Complete job
        store.update_job(
            job_id,
            status='completed',
            files_found=1,
            files_processed=1,
            errors_count=0
        )
        
        # Verify results
        with store.session() as session:
            from kairix_offline.stores.sqlite.models import (
                Conversation, ConversationFragment, Summary, Embedding
            )
            
            # Check conversation
            conversations = session.query(Conversation).all()
            assert len(conversations) == 1
            assert conversations[0].file_name == "test_conversation.json"
            
            # Check fragments
            fragments = session.query(ConversationFragment).all()
            assert len(fragments) == 4
            assert fragments[0].content == "What is Python?"
            
            # Check summaries
            summaries = session.query(Summary).all()
            assert len(summaries) == 4
            
            # Check embeddings
            embeddings = session.query(Embedding).all()
            assert len(embeddings) == 4
            assert embeddings[0].dimensions == 768