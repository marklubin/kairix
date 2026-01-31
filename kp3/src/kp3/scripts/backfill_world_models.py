"""Backfill script for world model extraction.

Processes historical passages sequentially to build world model history
using the fold semantic (each passage conditioned on prior state).
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kp3.config import get_settings
from kp3.db.models import Passage, ProcessingRun
from kp3.processors.base import ProcessorGroup
from kp3.processors.world_model import WorldModelConfig, WorldModelProcessor

logger = logging.getLogger(__name__)


async def backfill_world_models(
    session: AsyncSession,
    *,
    branch: str = "HEAD",
    llm_model: str = "deepseek-chat",
    limit: int | None = None,
    dry_run: bool = False,
    passage_type: str = "memory_shard",
) -> dict[str, Any]:
    """Process historical passages sequentially to build world model history.

    Args:
        session: Database session
        branch: Ref branch name (e.g., "HEAD", "experiment-v2")
        llm_model: LLM model to use
        limit: Maximum number of passages to process (None = all)
        dry_run: If True, don't update refs
        passage_type: Type of passages to process

    Returns:
        Dict with statistics about the run
    """
    logger.info("Starting world model backfill (branch=%s, dry_run=%s)", branch, dry_run)

    # Build config
    config = WorldModelConfig(
        llm_model=llm_model,
        human_ref=f"world/human/{branch}",
        persona_ref=f"world/persona/{branch}",
        world_ref=f"world/world/{branch}",
        update_refs=not dry_run,
        fire_hooks=False,  # Don't fire hooks during backfill
    )

    # Query passages in temporal order
    stmt = (
        select(Passage)
        .where(Passage.passage_type == passage_type)
        .order_by(Passage.created_at.asc())
    )
    if limit:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    passages = list(result.scalars().all())

    total = len(passages)
    logger.info("Found %d passages to process", total)

    if total == 0:
        return {"total": 0, "processed": 0, "errors": 0}

    # Create processing run record
    run = ProcessingRun(
        input_sql=f"SELECT passages WHERE type = '{passage_type}' ORDER BY created_at",
        processor_type="world_model",
        processor_config=config.__dict__,
        status="running",
        total_groups=total,
        started_at=datetime.now(timezone.utc),
    )
    session.add(run)
    await session.flush()

    # Create processor
    processor = WorldModelProcessor(session)

    processed = 0
    errors = 0

    try:
        for i, passage in enumerate(passages, 1):
            logger.info("Processing passage %d/%d: %s", i, total, passage.id)

            group = ProcessorGroup(
                passage_ids=[passage.id],
                passages=[passage],
                group_key=str(passage.id),
                group_metadata={"created_at": str(passage.created_at)},
            )

            try:
                result = await processor.process(group, config)

                if result.action == "create":
                    processed += 1
                    logger.info("Created state passages for passage %s", passage.id)
                else:
                    logger.warning("Skipped passage %s (action=%s)", passage.id, result.action)

            except Exception as e:
                errors += 1
                logger.exception("Error processing passage %s: %s", passage.id, e)
                # Continue with next passage

            # Update progress
            run.processed_groups = i
            run.output_count = processed
            await session.flush()

            # Commit periodically to avoid losing work
            if i % 10 == 0:
                await session.commit()

        # Final commit
        await session.commit()

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)

    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = datetime.now(timezone.utc)
        logger.exception("Backfill failed: %s", e)
        raise

    finally:
        await session.flush()

    stats = {
        "run_id": str(run.id),
        "total": total,
        "processed": processed,
        "errors": errors,
        "branch": branch,
        "dry_run": dry_run,
    }

    logger.info("Backfill complete: %s", stats)
    return stats


async def main(
    branch: str = "HEAD",
    llm_model: str = "deepseek-chat",
    limit: int | None = None,
    dry_run: bool = False,
    passage_type: str = "memory_shard",
) -> dict[str, Any]:
    """Run backfill as standalone script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        stats = await backfill_world_models(
            session,
            branch=branch,
            llm_model=llm_model,
            limit=limit,
            dry_run=dry_run,
            passage_type=passage_type,
        )

    await engine.dispose()
    return stats


if __name__ == "__main__":
    import sys

    # Simple CLI for testing
    dry_run = "--dry-run" in sys.argv
    limit = None

    for arg in sys.argv[1:]:
        if arg.startswith("--limit="):
            limit = int(arg.split("=")[1])

    asyncio.run(main(dry_run=dry_run, limit=limit))
