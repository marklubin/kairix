import pytest
import uuid
from kairix.types import SourceDocument, MemoryShard, Summary, Embedding, Agent
from kairix import SummaryMemorySynth


class TestSummaryMemorySynthIntegration:
    """Integration tests for summary memory synthesis with real Neo4j database"""
    
    def test_summarize_single_document(self, mock_kairix_module, mock_llm, mock_embedder, mock_chunker):
        """Test summarizing a single document creates proper graph structure"""
        # Create a source document with fixed UID
        doc = SourceDocument(
            uid="test-doc-001",
            source_label="Test Document",
            source_type="test",
            content="This is a test document with some content that needs to be summarized and processed."
        )
        doc.save()
        
        # Create an agent with fixed name
        agent = Agent(name="test-agent-001")
        agent.save()
        
        # Create synth instance with mocked components
        synth = SummaryMemorySynth()
        synth.chunker = mock_chunker
        synth.embedding_transformer = mock_embedder
        synth.llm_text_generator = mock_llm
        
        # Run the summarization
        results = synth.synthesize_memories(
            agent=agent,
            prompt_file="default",
            max_tokens=512,
            temperature=0.7,
            chunk_size=100
        )
        
        # Verify the result
        assert results is not None
        assert len(results) > 0
        
        # Verify database state - look for specific test records
        # Check that test memory shards were created
        test_shards = MemoryShard.nodes.filter(uid__startswith="test-shard-")
        assert len(test_shards) > 0
        
        # Check that test summaries were created
        test_summaries = Summary.nodes.filter(uid__startswith="test-summary-")
        assert len(test_summaries) > 0
        
        # Check that test embeddings were created
        test_embeddings = Embedding.nodes.filter(uid__startswith="test-embedding-")
        assert len(test_embeddings) > 0
        
        # Verify the specific shard has the correct relationships
        shard = results[0]
        assert shard.agent.single().name == "test-agent-001"
        assert shard.source_document.single().uid == "test-doc-001"
        assert shard.summary.single() is not None
        assert shard.embedding.single() is not None
        
    def test_summarize_multiple_documents(self, mock_kairix_module, mock_llm, mock_embedder, mock_chunker):
        """Test summarizing multiple documents"""
        # Create multiple source documents with fixed UIDs
        docs = []
        doc_uids = ["test-doc-002", "test-doc-003", "test-doc-004"]
        for i, uid in enumerate(doc_uids):
            doc = SourceDocument(
                uid=uid,
                source_label=f"Test Document {i}",
                source_type="test",
                content=f"This is test document {i} with unique content for testing."
            )
            doc.save()
            docs.append(doc)
        
        # Create an agent with fixed name
        agent = Agent(name="test-agent-multi-001")
        agent.save()
        
        # Create synth instance with mocked components
        synth = SummaryMemorySynth()
        synth.chunker = mock_chunker
        synth.embedding_transformer = mock_embedder
        synth.llm_text_generator = mock_llm
        
        # Run summarization - it processes all documents at once
        results = synth.synthesize_memories(
            agent=agent,
            prompt_file="default",
            max_tokens=512,
            temperature=0.7,
            chunk_size=100
        )
        
        # Verify results
        assert results is not None
        assert len(results) >= 3  # At least one shard per document
        
        # Verify database state - look for specific test records
        test_shards = MemoryShard.nodes.filter(uid__startswith="test-shard-")
        assert len(test_shards) >= 3  # At least one shard per document
        
        # Verify shards are connected to the correct agent
        for shard in results:
            assert shard.agent.single().name == "test-agent-multi-001"
            assert shard.source_document.single().uid in ["test-doc-002", "test-doc-003", "test-doc-004"]
    
    def test_summarize_long_document(self, mock_kairix_module, mock_llm, mock_embedder, mock_chunker):
        """Test summarizing a long document that will create multiple chunks"""
        # Create a long document with fixed UID
        long_content = " ".join([f"Sentence {i} with some content." for i in range(100)])
        doc = SourceDocument(
            uid="test-doc-long-001",
            source_label="Long Document",
            source_type="test",
            content=long_content
        )
        doc.save()
        
        # Create an agent with fixed name
        agent = Agent(name="test-agent-long-001")
        agent.save()
        
        # Create synth instance with mocked components
        synth = SummaryMemorySynth()
        synth.chunker = mock_chunker
        synth.embedding_transformer = mock_embedder
        synth.llm_text_generator = mock_llm
        
        # Run the summarization
        results = synth.synthesize_memories(
            agent=agent,
            prompt_file="default",
            max_tokens=512,
            temperature=0.7,
            chunk_size=100
        )
        
        # Verify multiple memory shards were created (due to chunking)
        test_shards = MemoryShard.nodes.filter(uid__startswith="test-shard-")
        assert len(test_shards) > 1  # Should have multiple chunks
        
        # Verify each shard has proper relationships
        for shard in results:
            assert shard.summary.single() is not None
            assert shard.embedding.single() is not None
            assert shard.agent.single().name == "test-agent-long-001"
            assert shard.source_document.single().uid == "test-doc-long-001"
    
    def test_document_relationships(self, mock_kairix_module, mock_llm, mock_embedder, mock_chunker):
        """Test that all relationships are properly created"""
        # Create a source document with fixed UID
        doc = SourceDocument(
            uid="test-doc-rel-001",
            source_label="Relationship Test",
            source_type="test",
            content="Content for testing relationships in the graph."
        )
        doc.save()
        
        # Create an agent with fixed name
        agent = Agent(name="test-agent-rel-001")
        agent.save()
        
        # Create synth instance with mocked components
        synth = SummaryMemorySynth()
        synth.chunker = mock_chunker
        synth.embedding_transformer = mock_embedder
        synth.llm_text_generator = mock_llm
        
        # Run the summarization
        results = synth.synthesize_memories(
            agent=agent,
            prompt_file="default",
            max_tokens=512,
            temperature=0.7,
            chunk_size=100
        )
        
        # Get the created memory shard
        shard = results[0]
        shard_from_db = MemoryShard.nodes.get(uid=shard.uid)
        
        # Verify all relationships exist
        assert shard_from_db.source_document.single().uid == "test-doc-rel-001"
        assert shard_from_db.agent.single().name == "test-agent-rel-001"
        assert shard_from_db.summary.single() is not None
        assert shard_from_db.embedding.single() is not None
        
        # Verify specific test records were created
        assert shard_from_db.uid.startswith("test-shard-")
        assert shard_from_db.summary.single().uid.startswith("test-summary-")
        assert shard_from_db.embedding.single().uid.startswith("test-embedding-")
    
    def test_empty_document(self, mock_kairix_module, mock_llm, mock_embedder, mock_chunker):
        """Test handling of empty document"""
        # Create an empty document with fixed UID
        doc = SourceDocument(
            uid="test-doc-empty-001",
            source_label="Empty Document",
            source_type="test",
            content=""
        )
        doc.save()
        
        # Create an agent with fixed name
        agent = Agent(name="test-agent-empty-001")
        agent.save()
        
        # Create synth instance with mocked components
        synth = SummaryMemorySynth()
        synth.chunker = mock_chunker
        synth.embedding_transformer = mock_embedder
        synth.llm_text_generator = mock_llm
        
        # Run the summarization - should handle empty content gracefully
        results = synth.synthesize_memories(
            agent=agent,
            prompt_file="default",
            max_tokens=512,
            temperature=0.7,
            chunk_size=100
        )
        
        # Empty documents might not create shards depending on chunker behavior
        # Test should pass without errors
        assert results is not None
        
    def test_idempotent_summarization(self, mock_kairix_module, mock_llm, mock_embedder, mock_chunker):
        """Test that summarizing the same document twice doesn't create duplicates"""
        # Create a source document with fixed UID
        doc = SourceDocument(
            uid="test-doc-idem-001",
            source_label="Idempotent Test",
            source_type="test",
            content="Content for testing idempotent behavior."
        )
        doc.save()
        
        # Create an agent with fixed name
        agent = Agent(name="test-agent-idem-001")
        agent.save()
        
        # Create synth instance with mocked components
        synth = SummaryMemorySynth()
        synth.chunker = mock_chunker
        synth.embedding_transformer = mock_embedder
        synth.llm_text_generator = mock_llm
        
        # Run summarization twice
        results1 = synth.synthesize_memories(
            agent=agent,
            prompt_file="default",
            max_tokens=512,
            temperature=0.7,
            chunk_size=100
        )
        initial_shard_count = len(MemoryShard.nodes.all())
        
        results2 = synth.synthesize_memories(
            agent=agent,
            prompt_file="default",
            max_tokens=512,
            temperature=0.7,
            chunk_size=100
        )
        final_shard_count = len(MemoryShard.nodes.all())
        
        # Should not create additional shards - check only test shards
        test_shards_initial = MemoryShard.nodes.filter(uid__startswith="test-shard-")
        assert len(test_shards_initial) == len(results1)
        
        test_shards_final = MemoryShard.nodes.filter(uid__startswith="test-shard-")
        assert len(test_shards_final) == len(results1)  # Same count, no new shards created