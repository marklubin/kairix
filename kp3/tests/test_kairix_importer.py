"""Tests for Kairix SQLite importer."""

import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from kp3.db.models import Passage
from kp3.importers.kairix_sqlite import (
    SOURCE_SYSTEM,
    import_memory_shards,
    load_memory_shards,
)


def create_test_sqlite_db(path: Path, shards: list[dict[str, object]]) -> None:
    """Create a test SQLite database with memory_shards and agents tables."""
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # Create agents table
    cursor.execute("""
        CREATE TABLE agents (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
    """)

    # Create memory_shards table (simplified version of real schema)
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
            summary_id INTEGER,
            FOREIGN KEY (agent_id) REFERENCES agents(id)
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
            """
            INSERT INTO memory_shards (id, uid, contents, created_at, agent_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                shard.get("original_id", i),
                shard.get("uid", str(uuid4())),
                shard.get("contents"),
                shard.get("created_at"),
                agent_id,
            ),
        )

    conn.commit()
    conn.close()


class TestLoadMemoryShards:
    """Tests for loading shards from SQLite."""

    def test_load_empty_db(self) -> None:
        """Loading from empty database returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            create_test_sqlite_db(db_path, [])

            shards = load_memory_shards(db_path)

            assert shards == []

    def test_load_single_shard(self) -> None:
        """Loading single shard returns correct data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            create_test_sqlite_db(
                db_path,
                [
                    {
                        "original_id": 42,
                        "uid": "test-uid-123",
                        "contents": "Hello world",
                        "created_at": "2024-01-15T10:30:00Z",
                        "agent_name": "assistant",
                    }
                ],
            )

            shards = load_memory_shards(db_path)

            assert len(shards) == 1
            assert shards[0]["original_id"] == 42
            assert shards[0]["uid"] == "test-uid-123"
            assert shards[0]["contents"] == "Hello world"
            assert shards[0]["agent_name"] == "assistant"

    def test_load_multiple_shards(self) -> None:
        """Loading multiple shards preserves order by created_at."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            create_test_sqlite_db(
                db_path,
                [
                    {
                        "original_id": 1,
                        "uid": "uid-1",
                        "contents": "First",
                        "created_at": "2024-01-01T00:00:00Z",
                    },
                    {
                        "original_id": 2,
                        "uid": "uid-2",
                        "contents": "Second",
                        "created_at": "2024-01-02T00:00:00Z",
                    },
                    {
                        "original_id": 3,
                        "uid": "uid-3",
                        "contents": "Third",
                        "created_at": "2024-01-03T00:00:00Z",
                    },
                ],
            )

            shards = load_memory_shards(db_path)

            assert len(shards) == 3
            assert [s["contents"] for s in shards] == ["First", "Second", "Third"]


@pytest.mark.asyncio
class TestImportMemoryShards:
    """Tests for importing shards into kp3."""

    async def test_import_empty_db(self, session) -> None:  # type: ignore[no-untyped-def]
        """Importing empty database returns zero stats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            create_test_sqlite_db(db_path, [])

            stats = await import_memory_shards(session, db_path)

            assert stats.total_shards == 0
            assert stats.imported == 0
            assert stats.skipped_duplicate == 0
            assert stats.skipped_empty == 0

    async def test_import_single_shard(self, session) -> None:  # type: ignore[no-untyped-def]
        """Importing single shard creates passage with correct metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            create_test_sqlite_db(
                db_path,
                [
                    {
                        "original_id": 42,
                        "uid": "test-uid-123",
                        "contents": "Memory shard content here",
                        "created_at": "2024-01-15T10:30:00Z",
                        "agent_name": "assistant",
                    }
                ],
            )

            stats = await import_memory_shards(session, db_path)

            assert stats.total_shards == 1
            assert stats.imported == 1

            # Verify passage was created correctly
            result = await session.execute(
                select(Passage).where(Passage.source_external_id == "test-uid-123")
            )
            passage = result.scalar_one()

            assert passage.content == "Memory shard content here"
            assert passage.passage_type == "memory_shard"
            assert passage.source_system == SOURCE_SYSTEM
            assert passage.metadata_["original_id"] == 42
            assert passage.metadata_["agent_name"] == "assistant"
            assert "2024-01-15" in passage.metadata_["original_created_at"]

    async def test_import_skips_empty_content(self, session) -> None:  # type: ignore[no-untyped-def]
        """Shards with empty content are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            create_test_sqlite_db(
                db_path,
                [
                    {"uid": "uid-1", "contents": "Valid content"},
                    {"uid": "uid-2", "contents": ""},
                    {"uid": "uid-3", "contents": None},
                    {"uid": "uid-4", "contents": "   "},
                ],
            )

            stats = await import_memory_shards(session, db_path)

            assert stats.total_shards == 4
            assert stats.imported == 1
            assert stats.skipped_empty == 3

    async def test_import_skips_duplicates(self, session) -> None:  # type: ignore[no-untyped-def]
        """Re-importing same shards skips duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            create_test_sqlite_db(
                db_path,
                [
                    {"uid": "uid-1", "contents": "Content 1"},
                    {"uid": "uid-2", "contents": "Content 2"},
                ],
            )

            # First import
            stats1 = await import_memory_shards(session, db_path)
            assert stats1.imported == 2
            assert stats1.skipped_duplicate == 0

            # Second import - same data
            stats2 = await import_memory_shards(session, db_path)
            assert stats2.imported == 0
            assert stats2.skipped_duplicate == 2

    async def test_import_preserves_period_from_created_at(self, session) -> None:  # type: ignore[no-untyped-def]
        """Import sets period_start/end from original created_at."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            create_test_sqlite_db(
                db_path,
                [
                    {
                        "uid": "uid-1",
                        "contents": "Content",
                        "created_at": "2024-06-15T14:30:00Z",
                    }
                ],
            )

            await import_memory_shards(session, db_path)

            result = await session.execute(
                select(Passage).where(Passage.source_external_id == "uid-1")
            )
            passage = result.scalar_one()

            assert passage.period_start is not None
            assert passage.period_start.year == 2024
            assert passage.period_start.month == 6
            assert passage.period_start.day == 15
