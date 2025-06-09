import uuid

import pytest
from kairix_core.types import Embedding, MemoryShard, SourceDocument, Summary
from kairix_offline.processing import SummaryMemorySynth

# Import from conftest will happen at runtime


class Source:
    def __init__(self, *, title, text):
        self.title = title
        self.text = text


class SyntheizerTestCase:
    def __init__(self, *, sources: list[Source], agent_name: str, prefix: str):
        self.prefix = prefix
        self.agent_name = agent_name
        self.sources = sources


@pytest.mark.integration
class TestSummaryMemorySynthIntegration:
    """Integration tests for summary memory synthesis with real Neo4j database"""

    @pytest.fixture
    def synthezier(self, mock_inference_provider, mock_embedder, mock_chunker):
        return SummaryMemorySynth(
            chunker=mock_chunker,
            embedder=mock_embedder,
            inference_provider=mock_inference_provider,
        )

    @pytest.mark.parametrize(
        "test_case",
        [
            SyntheizerTestCase(
                sources=[
                    Source(
                        title="Basic Document",
                        text="This is a simple test document with basic content.",
                    )
                ],
                agent_name="BasicAgent",
                prefix="basic",
            ),
            SyntheizerTestCase(
                sources=[
                    Source(title="Doc 1", text="First document content"),
                    Source(title="Doc 2", text="Second document content"),
                    Source(title="Doc 3", text="Third document content"),
                ],
                agent_name="MultiAgent",
                prefix="multi",
            ),
            SyntheizerTestCase(
                sources=[Source(title="Empty Doc", text="")],
                agent_name="EmptyAgent",
                prefix="empty",
            ),
            SyntheizerTestCase(
                sources=[
                    Source(
                        title="Long Document",
                        text="This is a very long document. " * 100,
                    )
                ],
                agent_name="LongAgent",
                prefix="long",
            ),
            SyntheizerTestCase(
                sources=[
                    Source(
                        title="Technical Doc",
                        text="API endpoint /users returns JSON {id: int, name: string}",
                    ),
                    Source(
                        title="Business Doc",
                        text="Q4 revenue increased by 25% YoY to $1.2M",
                    ),
                    Source(
                        title="Research Paper",
                        text="Neural networks exhibit emergent behavior at scale",
                    ),
                ],
                agent_name="MixedAgent",
                prefix="mixed",
            ),
        ],
    )
    def test_synth(self, synthezier: SummaryMemorySynth, test_case: SyntheizerTestCase):
        for source in test_case.sources:
            document = SourceDocument(
                uid=str(uuid.uuid4()),
                source_label=source.title,
                source_type="test",
                content=source.text,
            )

            document.save()

        synthezier.synthesize_memories(test_case.agent_name, test_case.prefix)

        # each document will be chunked into 5 chunks
        expected_chunks_per_doc = 5
        total_expected_chunks = len(test_case.sources) * expected_chunks_per_doc

        # verify embeddings exist for each chunk, all embeddies are the same randomly generated
        # vector
        embeddings = list(Embedding.nodes.all())
        assert len(embeddings) == total_expected_chunks

        # All embeddings should have the same vector (from mock)
        from conftest import VECTOR_EMBEDDING

        for embedding in embeddings:
            assert embedding.vector == VECTOR_EMBEDDING
            assert embedding.uid.startswith(test_case.prefix)

        # verify summaries exist for each chunk,  Each summary is a hard coded string
        summaries = list(Summary.nodes.all())
        assert len(summaries) == total_expected_chunks

        # All summaries should have the same text (from mock)
        from conftest import SUMMARY_TEXT

        for summary in summaries:
            assert summary.summary_text == SUMMARY_TEXT
            assert summary.uid.startswith(test_case.prefix)

        # verify shards for each chunk
        shards = list(MemoryShard.nodes.all())
        assert len(shards) == total_expected_chunks

        # Verify each shard has correct properties and relationships
        for shard in shards:
            assert shard.uid.startswith(test_case.prefix)
            assert shard.shard_contents == SUMMARY_TEXT
            assert shard.vector_address == VECTOR_EMBEDDING

            # Verify relationships
            assert shard.summary.single() is not None
            assert shard.embedding.single() is not None
            assert shard.source_document.single() is not None

            # Verify source document relationship
            source_doc = shard.source_document.single()
            assert source_doc.source_type == "test"

            # Verify the shard's embedding and summary match
            assert shard.summary.single().summary_text == SUMMARY_TEXT
            assert shard.embedding.single().vector == VECTOR_EMBEDDING
