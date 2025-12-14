"""End-to-end tests for the full processing pipeline.

Tests the complete flow: import → embed → aggregation.
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import anthropic
import pytest
from sqlalchemy import select

from kp3.db.models import Passage, PassageDerivation
from kp3.importers.kairix_sqlite import import_memory_shards
from kp3.processors.embedding import EmbeddingProcessor
from kp3.processors.llm_prompt import LLMPromptProcessor
from kp3.services.runs import create_run, execute_run


def _mock_anthropic_response(content: str) -> anthropic.types.Message:
    """Create a mock Anthropic message response."""
    return anthropic.types.Message(
        id="msg_test",
        type="message",
        role="assistant",
        content=[anthropic.types.TextBlock(type="text", text=content)],
        model="claude-3-haiku-20240307",
        stop_reason="end_turn",
        usage=anthropic.types.Usage(input_tokens=10, output_tokens=20),
    )


def create_test_kairix_db(path: Path, shards: list[dict[str, object]]) -> None:
    """Create a test Kairix SQLite database."""
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE agents (id INTEGER PRIMARY KEY, name TEXT)
    """)
    cursor.execute("""
        CREATE TABLE memory_shards (
            id INTEGER PRIMARY KEY,
            uid TEXT NOT NULL,
            contents TEXT,
            embedding_type TEXT,
            embedding BLOB,
            created_at TEXT,
            agent_id INTEGER,
            source_object_id INTEGER,
            summary_id INTEGER
        )
    """)

    # Insert agents
    agents = {s.get("agent_name") for s in shards if s.get("agent_name")}
    agent_id_map: dict[str, int] = {}
    for i, name in enumerate(agents, 1):
        cursor.execute("INSERT INTO agents (id, name) VALUES (?, ?)", (i, name))
        agent_id_map[name] = i  # type: ignore[index]

    # Insert shards
    for i, shard in enumerate(shards, 1):
        agent_id = agent_id_map.get(shard.get("agent_name"))  # type: ignore[arg-type]
        cursor.execute(
            "INSERT INTO memory_shards (id, uid, contents, created_at, agent_id) VALUES (?, ?, ?, ?, ?)",
            (
                i,
                shard.get("uid", str(uuid4())),
                shard["contents"],
                shard.get("created_at"),
                agent_id,
            ),
        )

    conn.commit()
    conn.close()


@pytest.mark.asyncio
class TestE2EPipeline:
    """End-to-end pipeline tests."""

    async def test_import_then_embed(self, session) -> None:  # type: ignore[no-untyped-def]
        """Test importing shards and then generating embeddings."""
        # Step 1: Create and import test data
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            create_test_kairix_db(
                db_path,
                [
                    {
                        "uid": "shard-1",
                        "contents": "Today I learned about Python async programming.",
                        "created_at": "2024-01-15T10:00:00Z",
                        "agent_name": "assistant",
                    },
                    {
                        "uid": "shard-2",
                        "contents": "Had a meeting about the new project requirements.",
                        "created_at": "2024-01-15T14:00:00Z",
                        "agent_name": "assistant",
                    },
                    {
                        "uid": "shard-3",
                        "contents": "Reviewed the database schema design.",
                        "created_at": "2024-01-15T16:00:00Z",
                        "agent_name": "default",
                    },
                ],
            )

            import_stats = await import_memory_shards(session, db_path)

        assert import_stats.imported == 3

        # Verify passages were created
        result = await session.execute(
            select(Passage).where(Passage.passage_type == "memory_shard")
        )
        passages = list(result.scalars().all())
        assert len(passages) == 3

        # Step 2: Run embedding processor on imported passages
        mock_embedding = [0.1] * 1024

        with patch.object(
            EmbeddingProcessor,
            "_generate_embedding",
            new_callable=AsyncMock,
            return_value=mock_embedding,
        ):
            processor = EmbeddingProcessor()

            # Create run that selects all memory_shards
            run = await create_run(
                session,
                input_sql="""
                    SELECT
                        array_agg(id) as passage_ids,
                        id::text as group_key,
                        '{}'::jsonb as group_metadata
                    FROM passages
                    WHERE passage_type = 'memory_shard'
                    GROUP BY id
                """,
                processor_type="embedding",
                processor_config={"model": "test-model"},
            )

            run = await execute_run(session, run, processor)

        assert run.status == "completed"
        assert run.processed_groups == 3
        # Note: embedding processor uses "update" action, not "create", so output_count stays 0

        # Verify embeddings were added
        result = await session.execute(
            select(Passage).where(
                Passage.passage_type == "memory_shard",
                Passage.embedding_qwen3.isnot(None),
            )
        )
        embedded_passages = list(result.scalars().all())
        assert len(embedded_passages) == 3

    async def test_import_embed_then_aggregate(self, session) -> None:  # type: ignore[no-untyped-def]
        """Test full pipeline: import → embed → daily summary aggregation."""
        # Step 1: Import test data
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            create_test_kairix_db(
                db_path,
                [
                    {
                        "uid": "day1-shard-1",
                        "contents": "Started the day with code review.",
                        "created_at": "2024-01-15T09:00:00Z",
                    },
                    {
                        "uid": "day1-shard-2",
                        "contents": "Fixed a critical bug in the API.",
                        "created_at": "2024-01-15T11:00:00Z",
                    },
                    {
                        "uid": "day1-shard-3",
                        "contents": "Wrote documentation for the new feature.",
                        "created_at": "2024-01-15T15:00:00Z",
                    },
                ],
            )

            import_stats = await import_memory_shards(session, db_path)
        assert import_stats.imported == 3

        # Step 2: Run embedding processor
        mock_embedding = [0.1] * 1024

        with patch.object(
            EmbeddingProcessor,
            "_generate_embedding",
            new_callable=AsyncMock,
            return_value=mock_embedding,
        ):
            embed_run = await create_run(
                session,
                input_sql="""
                    SELECT
                        array_agg(id) as passage_ids,
                        id::text as group_key,
                        '{}'::jsonb as group_metadata
                    FROM passages
                    WHERE passage_type = 'memory_shard'
                    GROUP BY id
                """,
                processor_type="embedding",
                processor_config={},
            )

            embed_processor = EmbeddingProcessor()
            embed_run = await execute_run(session, embed_run, embed_processor)

        assert embed_run.status == "completed"

        # Step 3: Run LLM aggregation to create daily summary
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_anthropic_response(
                "Daily summary: Productive day with code review, bug fixes, and documentation work."
            )
        )

        # Group by day (all are same day in test data)
        agg_run = await create_run(
            session,
            input_sql="""
                SELECT
                    array_agg(id ORDER BY period_start) as passage_ids,
                    date_trunc('day', period_start)::text as group_key,
                    jsonb_build_object('date', date_trunc('day', period_start)) as group_metadata
                FROM passages
                WHERE passage_type = 'memory_shard'
                GROUP BY date_trunc('day', period_start)
            """,
            processor_type="llm_prompt",
            processor_config={
                "prompt_template": "Summarize these events from {date}:\n\n{passages}",
                "output_passage_type": "daily_summary",
            },
        )

        llm_processor = LLMPromptProcessor(client=mock_client)
        agg_run = await execute_run(session, agg_run, llm_processor)

        assert agg_run.status == "completed"
        assert agg_run.processed_groups == 1
        assert agg_run.output_count == 1

        # Verify daily summary was created
        result = await session.execute(
            select(Passage).where(Passage.passage_type == "daily_summary")
        )
        summaries = list(result.scalars().all())
        assert len(summaries) == 1
        assert "Daily summary" in summaries[0].content

        # Verify derivation links exist
        result = await session.execute(
            select(PassageDerivation).where(PassageDerivation.derived_passage_id == summaries[0].id)
        )
        derivations = list(result.scalars().all())
        assert len(derivations) == 3  # Derived from 3 memory shards

    async def test_rerun_import_skips_duplicates(self, session) -> None:  # type: ignore[no-untyped-def]
        """Test that re-importing same data skips duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            create_test_kairix_db(
                db_path,
                [
                    {"uid": "shard-1", "contents": "First shard"},
                    {"uid": "shard-2", "contents": "Second shard"},
                ],
            )

            # First import
            stats1 = await import_memory_shards(session, db_path)
            assert stats1.imported == 2

            # Second import - should skip all
            stats2 = await import_memory_shards(session, db_path)
            assert stats2.imported == 0
            assert stats2.skipped_duplicate == 2

        # Total passages should still be 2
        result = await session.execute(
            select(Passage).where(Passage.passage_type == "memory_shard")
        )
        passages = list(result.scalars().all())
        assert len(passages) == 2

    async def test_pipeline_with_multiple_days(self, session) -> None:  # type: ignore[no-untyped-def]
        """Test aggregation across multiple days creates separate summaries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            create_test_kairix_db(
                db_path,
                [
                    # Day 1 shards
                    {
                        "uid": "d1-1",
                        "contents": "Day 1 morning work",
                        "created_at": "2024-01-15T09:00:00Z",
                    },
                    {
                        "uid": "d1-2",
                        "contents": "Day 1 afternoon work",
                        "created_at": "2024-01-15T14:00:00Z",
                    },
                    # Day 2 shards
                    {
                        "uid": "d2-1",
                        "contents": "Day 2 morning work",
                        "created_at": "2024-01-16T09:00:00Z",
                    },
                    {
                        "uid": "d2-2",
                        "contents": "Day 2 afternoon work",
                        "created_at": "2024-01-16T14:00:00Z",
                    },
                ],
            )

            await import_memory_shards(session, db_path)

        # Run aggregation
        call_count = 0

        def mock_create(*args: object, **kwargs: object) -> anthropic.types.Message:
            nonlocal call_count
            call_count += 1
            return _mock_anthropic_response(f"Summary for day {call_count}")

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=mock_create)

        agg_run = await create_run(
            session,
            input_sql="""
                SELECT
                    array_agg(id ORDER BY period_start) as passage_ids,
                    date_trunc('day', period_start)::text as group_key,
                    jsonb_build_object('date', date_trunc('day', period_start)) as group_metadata
                FROM passages
                WHERE passage_type = 'memory_shard'
                GROUP BY date_trunc('day', period_start)
                ORDER BY date_trunc('day', period_start)
            """,
            processor_type="llm_prompt",
            processor_config={
                "prompt_template": "Summarize: {passages}",
                "output_passage_type": "daily_summary",
            },
        )

        llm_processor = LLMPromptProcessor(client=mock_client)
        agg_run = await execute_run(session, agg_run, llm_processor)

        assert agg_run.status == "completed"
        assert agg_run.processed_groups == 2
        assert agg_run.output_count == 2

        # Verify two separate summaries were created
        result = await session.execute(
            select(Passage)
            .where(Passage.passage_type == "daily_summary")
            .order_by(Passage.period_start)
        )
        summaries = list(result.scalars().all())
        assert len(summaries) == 2
