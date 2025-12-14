"""Tests for runs service."""

from sqlalchemy.ext.asyncio import AsyncSession

from kp3.processors.base import Processor, ProcessorGroup, ProcessorResult
from kp3.services.derivations import get_sources
from kp3.services.passages import create_passage, get_passage
from kp3.services.runs import create_run, execute_run, get_run, list_runs


class MockConfig:
    """Mock config for testing."""

    pass


class MockProcessor(Processor[MockConfig]):
    """Mock processor for testing."""

    def __init__(self, results: list[ProcessorResult] | None = None):
        self._results = results or []
        self._call_count = 0

    async def process(self, group: ProcessorGroup, config: MockConfig) -> ProcessorResult:
        if self._results:
            result = self._results[self._call_count % len(self._results)]
        else:
            # Default: create a summary (passage_type comes from run config)
            result = ProcessorResult(
                action="create",
                content=f"Summary of {len(group.passages)} passages",
                metadata={"group_key": group.group_key},
            )
        self._call_count += 1
        return result

    @classmethod
    def parse_config(cls, raw: dict) -> MockConfig:
        """Parse config - mock just returns empty config."""
        return MockConfig()

    @property
    def processor_type(self) -> str:
        return "mock"


async def test_create_run(session: AsyncSession):
    """Create a processing run."""
    run = await create_run(
        session,
        input_sql="SELECT array_agg(id) as passage_ids, 'all' as group_key FROM passages",
        processor_type="mock",
        processor_config={"foo": "bar"},
    )

    assert run.id is not None
    assert run.status == "pending"
    assert run.processor_type == "mock"
    assert run.processor_config == {"foo": "bar"}


async def test_get_run(session: AsyncSession):
    """Retrieve run by ID."""
    created = await create_run(
        session,
        input_sql="SELECT ...",
        processor_type="test",
        processor_config={},
    )
    await session.commit()

    found = await get_run(session, created.id)
    assert found is not None
    assert found.id == created.id


async def test_list_runs(session: AsyncSession):
    """List runs with status filter."""
    run1 = await create_run(session, "SELECT 1", "a", {})
    run2 = await create_run(session, "SELECT 2", "b", {})
    run2.status = "completed"
    await session.commit()

    all_runs = await list_runs(session)
    assert len(all_runs) == 2

    pending = await list_runs(session, status="pending")
    assert len(pending) == 1
    assert pending[0].id == run1.id

    completed = await list_runs(session, status="completed")
    assert len(completed) == 1
    assert completed[0].id == run2.id


async def test_execute_run_create(session: AsyncSession):
    """Execute run that creates new passages."""
    # Create source passages
    p1 = await create_passage(session, content="Day 1 events", passage_type="raw")
    p2 = await create_passage(session, content="Day 1 more", passage_type="raw")
    await session.commit()

    # Create run with SQL that groups all passages
    run = await create_run(
        session,
        input_sql=f"""
            SELECT
                ARRAY['{p1.id}'::uuid, '{p2.id}'::uuid] as passage_ids,
                'day1' as group_key,
                '{{"count": 2}}'::jsonb as group_metadata
        """,
        processor_type="mock",
        processor_config={"output_passage_type": "summary"},
    )
    await session.commit()

    # Execute with mock processor
    processor = MockProcessor()
    run = await execute_run(session, run, processor)
    await session.commit()

    assert run.status == "completed"
    assert run.total_groups == 1
    assert run.processed_groups == 1
    assert run.output_count == 1
    assert run.started_at is not None
    assert run.completed_at is not None

    # Find the created passage
    from sqlalchemy import select

    from kp3.db.models import Passage

    stmt = select(Passage).where(Passage.passage_type == "summary")
    result = await session.execute(stmt)
    summaries = list(result.scalars().all())

    assert len(summaries) == 1
    assert "Summary of 2 passages" in summaries[0].content

    # Check derivations
    sources = await get_sources(session, summaries[0].id)
    source_ids = {s.id for s in sources}
    assert p1.id in source_ids
    assert p2.id in source_ids


async def test_execute_run_update(session: AsyncSession):
    """Execute run that updates existing passage."""
    # Create a passage to update
    passage = await create_passage(session, content="Original", passage_type="raw")
    await session.commit()

    original_id = passage.id

    # Create run
    run = await create_run(
        session,
        input_sql=f"""
            SELECT
                ARRAY['{passage.id}'::uuid] as passage_ids,
                'update_group' as group_key
        """,
        processor_type="mock",
        processor_config={},
    )
    await session.commit()

    # Processor that returns update action
    processor = MockProcessor(
        results=[
            ProcessorResult(
                action="update",
                passage_id=passage.id,
                updates={"content": "Updated content"},
            )
        ]
    )

    await execute_run(session, run, processor)
    await session.commit()

    # Check passage was updated
    updated = await get_passage(session, original_id)
    assert updated is not None
    assert updated.content == "Updated content"

    # Check archive was created
    from sqlalchemy import select

    from kp3.db.models import PassageArchive

    stmt = select(PassageArchive).where(PassageArchive.id == original_id)
    result = await session.execute(stmt)
    archives = list(result.scalars().all())

    assert len(archives) == 1
    assert archives[0].content == "Original"


async def test_execute_run_pass(session: AsyncSession):
    """Execute run where processor passes (no action)."""
    passage = await create_passage(session, content="Skip me", passage_type="raw")
    await session.commit()

    run = await create_run(
        session,
        input_sql=f"""
            SELECT
                ARRAY['{passage.id}'::uuid] as passage_ids,
                'skip' as group_key
        """,
        processor_type="mock",
        processor_config={},
    )
    await session.commit()

    processor = MockProcessor(results=[ProcessorResult(action="pass")])
    await execute_run(session, run, processor)
    await session.commit()

    assert run.status == "completed"
    assert run.output_count == 0


async def test_execute_run_multiple_groups(session: AsyncSession):
    """Execute run with multiple groups."""
    p1 = await create_passage(session, content="Group A item 1", passage_type="raw")
    p2 = await create_passage(session, content="Group A item 2", passage_type="raw")
    p3 = await create_passage(session, content="Group B item 1", passage_type="raw")
    await session.commit()

    run = await create_run(
        session,
        input_sql=f"""
            SELECT * FROM (VALUES
                (ARRAY['{p1.id}'::uuid, '{p2.id}'::uuid], 'group_a'),
                (ARRAY['{p3.id}'::uuid], 'group_b')
            ) AS t(passage_ids, group_key)
        """,
        processor_type="mock",
        processor_config={},
    )
    await session.commit()

    processor = MockProcessor()
    await execute_run(session, run, processor)
    await session.commit()

    assert run.total_groups == 2
    assert run.processed_groups == 2
    assert run.output_count == 2
