"""Import memory shards from Kairix SQLite backup."""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from kp3.services.passages import create_passage, get_passage_by_external_id

logger = logging.getLogger(__name__)

SOURCE_SYSTEM = "kairix_backup"


@dataclass
class ImportStats:
    """Statistics from an import operation."""

    total_shards: int = 0
    imported: int = 0
    skipped_duplicate: int = 0
    skipped_empty: int = 0


def _parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse a SQLite timestamp string to datetime."""
    if not ts_str:
        return None
    try:
        # Handle ISO format with or without timezone
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        logger.warning("Failed to parse timestamp: %s", ts_str)
        return None


def load_memory_shards(db_path: Path) -> list[dict[str, object]]:
    """Load memory shards from SQLite database.

    Joins with agents table to get agent name.

    Returns list of dicts with:
        - uid: unique identifier for deduplication
        - contents: the text content
        - created_at: original creation timestamp
        - agent_name: name of the agent (if available)
        - original_id: the numeric ID from source
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Join with agents to get agent name
    query = """
        SELECT
            ms.id,
            ms.uid,
            ms.contents,
            ms.created_at,
            a.name as agent_name
        FROM memory_shards ms
        LEFT JOIN agents a ON ms.agent_id = a.id
        ORDER BY ms.created_at
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    shards = []
    for row in rows:
        shards.append(
            {
                "original_id": row["id"],
                "uid": row["uid"],
                "contents": row["contents"],
                "created_at": row["created_at"],
                "agent_name": row["agent_name"],
            }
        )

    return shards


async def import_memory_shards(
    session: AsyncSession,
    db_path: Path,
    *,
    batch_size: int = 100,
) -> ImportStats:
    """Import memory shards from a Kairix SQLite backup.

    Args:
        session: Database session
        db_path: Path to the SQLite database file
        batch_size: Commit every N passages

    Returns:
        ImportStats with counts of imported/skipped passages
    """
    stats = ImportStats()

    shards = load_memory_shards(db_path)
    stats.total_shards = len(shards)
    logger.info("Found %d memory shards in %s", stats.total_shards, db_path)

    for i, shard in enumerate(shards, 1):
        uid = str(shard["uid"])
        contents = shard["contents"]

        # Skip empty content
        if not contents or not str(contents).strip():
            stats.skipped_empty += 1
            continue

        # Check if already imported (by external ID)
        existing = await get_passage_by_external_id(session, SOURCE_SYSTEM, uid)
        if existing:
            stats.skipped_duplicate += 1
            continue

        # Parse timestamp for period tracking
        original_created_at = _parse_timestamp(
            str(shard["created_at"]) if shard["created_at"] else None
        )

        # Build metadata with back-reference to original shard
        metadata = {
            "original_id": shard["original_id"],
            "original_created_at": original_created_at.isoformat() if original_created_at else None,
        }
        if shard["agent_name"]:
            metadata["agent_name"] = shard["agent_name"]

        # Create passage
        await create_passage(
            session,
            content=str(contents),
            passage_type="memory_shard",
            period_start=original_created_at,
            period_end=original_created_at,
            metadata=metadata,
            source_system=SOURCE_SYSTEM,
            source_external_id=uid,
        )
        stats.imported += 1

        if i % batch_size == 0:
            logger.info("Progress: %d/%d shards processed", i, stats.total_shards)
            await session.flush()

    logger.info(
        "Import complete: %d imported, %d duplicates, %d empty",
        stats.imported,
        stats.skipped_duplicate,
        stats.skipped_empty,
    )

    return stats
