"""Processing run execution service."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import Passage, ProcessingRun
from kp3.processors.base import ProcessorGroup, ProcessorResult
from kp3.services.derivations import create_derivations
from kp3.services.passages import archive_passage, create_passage

if TYPE_CHECKING:
    from kp3.processors.base import Processor

logger = logging.getLogger(__name__)


async def create_run(
    session: AsyncSession,
    input_sql: str,
    processor_type: str,
    processor_config: dict,
) -> ProcessingRun:
    """Create a new processing run."""
    run = ProcessingRun(
        input_sql=input_sql,
        processor_type=processor_type,
        processor_config=processor_config,
        status="pending",
    )
    session.add(run)
    await session.flush()
    return run


async def get_run(session: AsyncSession, run_id: UUID) -> ProcessingRun | None:
    """Get a processing run by ID."""
    return await session.get(ProcessingRun, run_id)


async def list_runs(
    session: AsyncSession,
    status: str | None = None,
    limit: int = 100,
) -> list[ProcessingRun]:
    """List processing runs, optionally filtered by status."""
    stmt = select(ProcessingRun).order_by(ProcessingRun.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(ProcessingRun.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def execute_run(
    session: AsyncSession,
    run: ProcessingRun,
    processor: "Processor",
) -> ProcessingRun:
    """Execute a processing run.

    Flow:
    1. Execute input_sql to get groups
    2. For each group, call processor
    3. Handle result (create, update, or pass)
    4. Track progress and update run status
    """
    logger.info("Starting run %s with processor %s", run.id, run.processor_type)
    logger.debug("Input SQL: %s", run.input_sql)
    logger.debug("Processor config: %s", run.processor_config)

    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    await session.flush()

    try:
        # Execute input SQL to get groups
        logger.info("Fetching groups from input SQL...")
        groups = await _fetch_groups(session, run.input_sql)
        run.total_groups = len(groups)
        logger.info("Found %d groups to process", len(groups))
        await session.flush()

        output_count = 0
        for i, group in enumerate(groups, 1):
            logger.info(
                "Processing group %d/%d: key=%s, passage_ids=%d",
                i,
                len(groups),
                group.group_key,
                len(group.passage_ids),
            )

            # Fetch actual passage objects
            group.passages = await _fetch_passages(session, group.passage_ids)
            logger.debug("Fetched %d passages for group %s", len(group.passages), group.group_key)

            # Process the group
            logger.info("Calling processor for group %s...", group.group_key)
            typed_config = processor.parse_config(run.processor_config)
            result = await processor.process(group, typed_config)
            logger.info("Processor returned action=%s for group %s", result.action, group.group_key)

            # Handle result
            if result.action == "create":
                logger.debug("Creating new passage from result...")
                created = await _handle_create(session, run, group, result)
                output_count += created
                logger.info("Created %d passage(s) for group %s", created, group.group_key)
            elif result.action == "update":
                logger.debug("Updating passage %s...", result.passage_id)
                await _handle_update(session, run, result)
                logger.info("Updated passage %s", result.passage_id)
            else:
                logger.debug("Skipping group %s (action=pass)", group.group_key)

            run.processed_groups = (run.processed_groups or 0) + 1
            run.output_count = output_count
            await session.flush()

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        logger.info(
            "Run %s completed: %d groups processed, %d outputs created",
            run.id,
            run.processed_groups,
            run.output_count,
        )

    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = datetime.now(timezone.utc)
        logger.exception("Run %s failed: %s", run.id, e)
        raise

    finally:
        await session.flush()

    return run


async def _fetch_groups(session: AsyncSession, input_sql: str) -> list[ProcessorGroup]:
    """Execute input SQL and parse into ProcessorGroups.

    Expected SQL result columns:
    - passage_ids: UUID[] array of passage IDs in this group
    - group_key: TEXT identifier for the group
    - group_metadata: JSONB optional metadata about the group
    """
    result = await session.execute(text(input_sql))
    rows = result.fetchall()

    groups = []
    for row in rows:
        passage_ids = row.passage_ids if hasattr(row, "passage_ids") else row[0]
        group_key = row.group_key if hasattr(row, "group_key") else row[1]
        group_metadata = (
            row.group_metadata
            if hasattr(row, "group_metadata")
            else (row[2] if len(row) > 2 else {})
        )

        groups.append(
            ProcessorGroup(
                passage_ids=passage_ids,
                passages=[],  # Filled in later
                group_key=str(group_key),
                group_metadata=group_metadata or {},
            )
        )

    return groups


async def _fetch_passages(session: AsyncSession, passage_ids: list[UUID]) -> list[Passage]:
    """Fetch passages by IDs, maintaining order."""
    if not passage_ids:
        return []

    stmt = select(Passage).where(Passage.id.in_(passage_ids))
    result = await session.execute(stmt)
    passages_by_id = {p.id: p for p in result.scalars().all()}

    # Return in original order
    return [passages_by_id[pid] for pid in passage_ids if pid in passages_by_id]


async def _handle_create(
    session: AsyncSession,
    run: ProcessingRun,
    group: ProcessorGroup,
    result: ProcessorResult,
) -> int:
    """Handle create action - create new passage and derivations."""
    if not result.content:
        return 0

    # output_passage_type comes from run config, not processor result
    output_passage_type = run.processor_config.get("output_passage_type", "processed")

    new_passage = await create_passage(
        session,
        content=result.content,
        passage_type=output_passage_type,
        metadata=result.metadata,
        period_start=result.period_start,
        period_end=result.period_end,
    )

    # Create derivation links to source passages
    await create_derivations(
        session,
        derived_passage_id=new_passage.id,
        source_passage_ids=group.passage_ids,
        processing_run_id=run.id,
    )

    return 1


async def _handle_update(
    session: AsyncSession,
    run: ProcessingRun,
    result: ProcessorResult,
) -> None:
    """Handle update action - archive old version and update passage."""
    if not result.passage_id or not result.updates:
        return

    passage = await session.get(Passage, result.passage_id)
    if not passage:
        return

    # Archive before updating
    await archive_passage(session, passage, run.id)

    # Apply updates
    for key, value in result.updates.items():
        if hasattr(passage, key):
            setattr(passage, key, value)

    # Update content hash if content changed
    if "content" in result.updates:
        from kp3.services.passages import compute_content_hash

        passage.content_hash = compute_content_hash(result.updates["content"])

    await session.flush()
