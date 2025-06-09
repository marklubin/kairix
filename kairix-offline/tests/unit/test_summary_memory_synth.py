import hashlib
import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

# Import directly to avoid the processing module __init__.py
import kairix_offline.processing.summary_memory_synth

Chunk = kairix_offline.processing.summary_memory_synth.Chunk
SummaryMemorySynth = kairix_offline.processing.summary_memory_synth.SummaryMemorySynth


@pytest.mark.unit
class TestSummaryMemorySynth:
    """Unit tests for SummaryMemorySynth class."""

    @pytest.fixture
    def mock_chunker(self):
        """Mock chunker that returns predictable chunks."""
        chunker = Mock()
        chunker.return_value = ["chunk1", "chunk2", "chunk3"]
        return chunker

    @pytest.fixture
    def mock_embedder(self):
        """Mock embedder that returns predictable embeddings."""
        embedder = Mock()
        embedder.encode.return_value = MagicMock(tolist=lambda: [0.1, 0.2, 0.3])
        embedder.model_card_data = Mock(model_name="test-model")
        return embedder

    @pytest.fixture
    def mock_inference_provider(self):
        """Mock inference_provider that returns predictable summaries."""
        inference_provider = Mock()
        # predict method returns a string directly
        inference_provider.predict.return_value = "Generated summary text"
        return inference_provider

    @pytest.fixture
    def synth(self, mock_chunker, mock_embedder, mock_inference_provider):
        """Create SummaryMemorySynth instance with mocked dependencies."""
        return SummaryMemorySynth(
            chunker=mock_chunker,
            embedder=mock_embedder,
            inference_provider=mock_inference_provider,
        )

    @pytest.fixture
    def mock_source_document(self):
        """Mock SourceDocument."""
        doc = Mock()
        doc.content = "This is test document content"
        doc.uid = "doc-123"
        return doc

    @pytest.fixture
    def mock_agent(self):
        """Mock Agent."""
        agent = Mock()
        agent.name = "test-agent"
        return agent

    def test_initialization(self, mock_chunker, mock_embedder, mock_inference_provider):
        """Test that SummaryMemorySynth initializes with correct dependencies."""
        synth = SummaryMemorySynth(
            chunker=mock_chunker,
            embedder=mock_embedder,
            inference_provider=mock_inference_provider,
        )
        assert synth.chunker == mock_chunker
        assert synth.embedder == mock_embedder
        assert synth.inference_provider == mock_inference_provider

    @patch("kairix_offline.processing.summary_memory_synth.Summary")
    def test_get_summary_creates_new(self, mock_summary_class, synth):
        """Test _get_summary creates new summary when none exists."""
        # Setup
        mock_summary_class.get_or_none.return_value = None
        mock_summary_instance = Mock()
        mock_summary_class.return_value = mock_summary_instance

        chunk = Mock()
        chunk.idempotency_key = "test-key"
        chunk.text = "test chunk text"

        # Execute
        result = synth._get_summary(chunk)

        # Verify
        mock_summary_class.get_or_none.assert_called_once_with("test-key")
        synth.inference_provider.predict.assert_called_once()
        # We don't need to check the exact prompt format, just that predict was called
        mock_summary_class.assert_called_once_with(
            uid="test-key", summary_text="Generated summary text"
        )
        mock_summary_instance.save.assert_called_once()
        assert result == mock_summary_instance

    @patch("kairix_offline.processing.summary_memory_synth.Summary")
    def test_get_summary_reuses_existing(self, mock_summary_class, synth):
        """Test _get_summary reuses existing summary (idempotency)."""
        # Setup
        existing_summary = Mock()
        mock_summary_class.get_or_none.return_value = existing_summary

        chunk = Mock()
        chunk.idempotency_key = "test-key"

        # Execute
        result = synth._get_summary(chunk)

        # Verify
        mock_summary_class.get_or_none.assert_called_once_with("test-key")
        synth.inference_provider.predict.assert_not_called()
        assert result == existing_summary

    @patch("kairix_offline.processing.summary_memory_synth.Embedding")
    def test_get_embedding_creates_new(self, mock_embedding_class, synth):
        """Test _get_embedding creates new embedding when none exists."""
        # Setup
        mock_embedding_class.get_or_none.return_value = None
        mock_embedding_instance = Mock()
        mock_embedding_class.return_value = mock_embedding_instance

        chunk = Mock()
        chunk.idempotency_key = "test-key"

        summary = Mock()
        summary.summary_text = "test summary"

        # Execute
        result = synth._get_embedding(chunk, summary)

        # Verify
        mock_embedding_class.get_or_none.assert_called_once_with("test-key")
        synth.embedder.encode.assert_called_once_with("test summary")
        mock_embedding_class.assert_called_once_with(
            uid="test-key", embedding_model="test-model", vector=[0.1, 0.2, 0.3]
        )
        mock_embedding_instance.save.assert_called_once()
        assert result == mock_embedding_instance

    @patch("kairix_offline.processing.summary_memory_synth.Embedding")
    def test_get_embedding_reuses_existing(self, mock_embedding_class, synth):
        """Test _get_embedding reuses existing embedding (idempotency)."""
        # Setup
        existing_embedding = Mock()
        mock_embedding_class.get_or_none.return_value = existing_embedding

        chunk = Mock()
        chunk.idempotency_key = "test-key"

        summary = Mock()

        # Execute
        result = synth._get_embedding(chunk, summary)

        # Verify
        mock_embedding_class.get_or_none.assert_called_once_with("test-key")
        synth.embedder.encode.assert_not_called()
        assert result == existing_embedding

    @patch("kairix_offline.processing.summary_memory_synth.SourceDocument")
    def test_get_chunks(self, mock_source_doc_class, synth, mock_source_document):
        """Test _get_chunks processes documents correctly."""
        # Setup
        mock_source_doc_class.nodes.all.return_value = [mock_source_document]
        key_prefix = "test-prefix"

        # Execute
        chunks = synth._get_chunks(key_prefix)

        # Verify
        assert len(chunks) == 3  # chunker returns 3 chunks
        synth.chunker.assert_called_once_with("This is test document content")

        # Check each chunk
        for i, chunk in enumerate(chunks):
            expected_text = f"chunk{i + 1}"
            expected_hash = hashlib.sha256(expected_text.encode()).hexdigest()
            expected_key = f"test-prefix-{expected_hash}"

            assert chunk.idempotency_key == expected_key
            assert chunk.text == expected_text
            assert chunk.source == mock_source_document

    @patch("kairix_offline.processing.summary_memory_synth.MemoryShard")
    def test_process_creates_new_shard(
        self, mock_shard_class, synth, mock_agent, mock_source_document
    ):
        """Test _process creates new MemoryShard when none exists."""
        # Setup
        mock_shard_class.get_or_none.return_value = None
        mock_shard_instance = Mock()
        mock_shard_class.return_value = mock_shard_instance

        # Mock relationships
        mock_shard_instance.embedding = Mock()
        mock_shard_instance.summary = Mock()
        mock_shard_instance.agent = Mock()
        mock_shard_instance.source_document = Mock()

        # Create chunk
        chunk = Mock()
        chunk.idempotency_key = "test-key"
        chunk.text = "test text"
        chunk.source = mock_source_document
        # Note: agent is not set on the chunk in current implementation

        # Mock the _get_summary and _get_embedding methods
        mock_summary = Mock(summary_text="test summary")
        mock_embedding = Mock(vector=[0.1, 0.2, 0.3])

        with (
            patch.object(synth, "_get_summary", return_value=mock_summary),
            patch.object(synth, "_get_embedding", return_value=mock_embedding),
        ):
            # Execute
            result = synth._process(chunk)

        # Verify shard creation
        mock_shard_class.get_or_none.assert_called_once_with("test-key")
        mock_shard_class.assert_called_once_with(
            uid="test-key",
            shard_contents="test summary",
            vector_address=[0.1, 0.2, 0.3],
        )
        mock_shard_instance.save.assert_called_once()

        # Verify relationships
        mock_shard_instance.embedding.connect.assert_called_once_with(mock_embedding)
        mock_shard_instance.summary.connect.assert_called_once_with(mock_summary)
        # Note: agent connection removed from implementation
        mock_shard_instance.source_document.connect.assert_called_once_with(
            mock_source_document
        )

        assert result == mock_shard_instance

    @patch("kairix_offline.processing.summary_memory_synth.Summary")
    @patch("kairix_offline.processing.summary_memory_synth.Embedding")
    @patch("kairix_offline.processing.summary_memory_synth.MemoryShard")
    def test_process_reuses_existing_shard(
        self,
        mock_shard_class,
        mock_embedding_class,
        mock_summary_class,
        synth,
        mock_agent,
        mock_source_document,
    ):
        """Test _process reuses existing MemoryShard (idempotency)."""
        # Setup
        existing_shard = Mock()
        mock_shard_class.get_or_none.return_value = existing_shard

        chunk = Mock()
        chunk.idempotency_key = "test-key"

        # Execute
        result = synth._process(chunk)

        # Verify
        mock_shard_class.get_or_none.assert_called_once_with("test-key")
        assert result == existing_shard
        # Should not create new shard or call save
        mock_shard_class.assert_not_called()

    @patch("kairix_offline.processing.summary_memory_synth.Agent")
    @patch("kairix_offline.processing.summary_memory_synth.MemoryShard")
    @patch("kairix_offline.processing.summary_memory_synth.SourceDocument")
    def test_synthesize_memories_implementation_issues(
        self, mock_source_doc_class, mock_shard_class, mock_agent_class, synth
    ):
        """Test synthesize_memories - NOTE: Implementation has issues with Chunk creation."""
        # Setup
        mock_agent = Mock(name="test-agent")
        mock_agent_nodes = Mock()
        mock_agent_nodes.first_or_none.return_value = None  # Agent doesn't exist
        mock_agent_class.nodes = mock_agent_nodes
        mock_agent_class.return_value = mock_agent

        # This test will fail due to implementation issues
        mock_source_doc_class.nodes.all.return_value = []
        mock_shard_class.nodes.all.return_value = []

        # Execute - will fail due to Chunk creation without agent
        result = synth.synthesize_memories("test-agent", "test-prefix")

        # If implementation was fixed, we would verify:
        mock_agent_nodes.first_or_none.assert_called_once_with(name="test-agent")
        mock_agent_class.assert_called_once_with(name="test-agent")
        mock_agent.save.assert_called_once()
        assert result == []  # No documents, so no shards

    def test_get_idempotency_key(self, synth):
        """Test __get_idempotency_key generates consistent hashes."""
        prefix = "test"
        text = "sample text"

        # Generate key twice
        key1 = synth._SummaryMemorySynth__get_idempotency_key(prefix, text)
        key2 = synth._SummaryMemorySynth__get_idempotency_key(prefix, text)

        # Verify consistency
        assert key1 == key2

        # Verify format
        expected_hash = hashlib.sha256(text.encode()).hexdigest()
        assert key1 == f"{prefix}-{expected_hash}"

        # Different text should give different key
        key3 = synth._SummaryMemorySynth__get_idempotency_key(prefix, "different text")
        assert key3 != key1

    def test_chunk_creation_without_agent(self):
        """Test that Chunk objects can be created without agent parameter."""
        # The Chunk class was updated to not require agent parameter
        mock_doc = Mock(content="test content")

        # This should work without agent parameter
        chunk = Chunk(idempotency_key="key", text="text", source=mock_doc)

        assert chunk.idempotency_key == "key"
        assert chunk.text == "text"
        assert chunk.source == mock_doc
        # Note: chunk doesn't have an agent attribute
