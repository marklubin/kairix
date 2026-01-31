"""Tests for tags service and API endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import Passage
from kp3.services.passages import create_passage
from kp3.services.tags import (
    attach_tag_to_passage,
    attach_tags_to_passage,
    canonicalize_tag_name,
    count_tags,
    create_tag,
    delete_tag,
    detach_tag_from_passage,
    get_or_create_tag,
    get_passage_tags,
    get_passages_by_tag,
    get_tag,
    get_tag_by_name,
    list_tags,
    update_tag,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_embedding() -> list[float]:
    """Return a mock embedding vector."""
    return [0.1] * 1024


@pytest.fixture
def mock_generate_embedding(mock_embedding: list[float]) -> AsyncMock:
    """Mock the embedding generation function."""
    mock = AsyncMock(return_value=mock_embedding)
    return mock


@pytest.fixture
async def sample_passage(db_session: AsyncSession) -> Passage:
    """Create a sample passage for testing."""
    passage = await create_passage(
        db_session,
        content="Sample passage about Python programming",
        passage_type="test",
        agent_id="test-agent",
    )
    await db_session.commit()
    await db_session.refresh(passage)
    return passage


@pytest.fixture
async def another_passage(db_session: AsyncSession) -> Passage:
    """Create another passage for testing."""
    passage = await create_passage(
        db_session,
        content="Another passage about machine learning",
        passage_type="test",
        agent_id="test-agent",
    )
    await db_session.commit()
    await db_session.refresh(passage)
    return passage


@pytest.fixture
async def passage_with_dates(db_session: AsyncSession) -> Passage:
    """Create a passage with period dates for timestamp filter testing."""
    now = datetime.now(timezone.utc)
    passage = await create_passage(
        db_session,
        content="Passage with dates for testing filters",
        passage_type="test",
        agent_id="test-agent",
        period_start=now - timedelta(days=7),
        period_end=now - timedelta(days=1),
    )
    await db_session.commit()
    await db_session.refresh(passage)
    return passage


# =============================================================================
# canonicalize_tag_name tests
# =============================================================================


def test_canonicalize_tag_name_lowercase() -> None:
    """Tags are lowercased."""
    assert canonicalize_tag_name("Python") == "python"
    assert canonicalize_tag_name("MACHINE LEARNING") == "machine learning"


def test_canonicalize_tag_name_whitespace() -> None:
    """Whitespace is normalized."""
    assert canonicalize_tag_name("  machine   learning  ") == "machine learning"
    assert canonicalize_tag_name("data\t\nscience") == "data science"


def test_canonicalize_tag_name_preserves_words() -> None:
    """Words are preserved, just normalized."""
    assert canonicalize_tag_name("Natural Language Processing") == "natural language processing"


# =============================================================================
# Tag CRUD tests
# =============================================================================


@pytest.mark.docker
async def test_create_tag(db_session: AsyncSession, mock_generate_embedding: AsyncMock) -> None:
    """Create a new tag."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag = await create_tag(
            db_session,
            name="Python",
            agent_id="test-agent",
            description="Python programming language",
        )
        await db_session.commit()

    assert tag.name == "Python"
    assert tag.canonical_key == "python"
    assert tag.description == "Python programming language"
    assert tag.agent_id == "test-agent"
    assert tag.passage_count == 0
    assert tag.embedding_openai is not None
    mock_generate_embedding.assert_called_once_with("Python: Python programming language")


@pytest.mark.docker
async def test_create_tag_without_description(
    db_session: AsyncSession, mock_generate_embedding: AsyncMock
) -> None:
    """Create a tag without description."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag = await create_tag(
            db_session,
            name="ML",
            agent_id="test-agent",
        )
        await db_session.commit()

    assert tag.name == "ML"
    assert tag.description is None
    mock_generate_embedding.assert_called_once_with("ML")


@pytest.mark.docker
async def test_create_tag_duplicate_raises_error(
    db_session: AsyncSession, mock_generate_embedding: AsyncMock
) -> None:
    """Creating a duplicate tag raises ValueError."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        await create_tag(db_session, name="Python", agent_id="test-agent")
        await db_session.commit()

        with pytest.raises(ValueError, match="already exists"):
            await create_tag(db_session, name="python", agent_id="test-agent")


@pytest.mark.docker
async def test_get_or_create_tag_creates_new(
    db_session: AsyncSession, mock_generate_embedding: AsyncMock
) -> None:
    """get_or_create_tag creates a new tag if it doesn't exist."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag = await get_or_create_tag(db_session, "NewTag", "test-agent")
        await db_session.commit()

    assert tag.name == "NewTag"
    assert tag.canonical_key == "newtag"


@pytest.mark.docker
async def test_get_or_create_tag_returns_existing(
    db_session: AsyncSession, mock_generate_embedding: AsyncMock
) -> None:
    """get_or_create_tag returns existing tag."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag1 = await get_or_create_tag(db_session, "Python", "test-agent")
        await db_session.commit()

        tag2 = await get_or_create_tag(db_session, "python", "test-agent")

    assert tag1.id == tag2.id


@pytest.mark.docker
async def test_get_tag_by_id(db_session: AsyncSession, mock_generate_embedding: AsyncMock) -> None:
    """Get a tag by its ID."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag = await create_tag(db_session, name="Test", agent_id="test-agent")
        await db_session.commit()

        fetched = await get_tag(db_session, tag.id, "test-agent")

    assert fetched is not None
    assert fetched.id == tag.id


@pytest.mark.docker
async def test_get_tag_wrong_agent(
    db_session: AsyncSession, mock_generate_embedding: AsyncMock
) -> None:
    """Can't get tag with wrong agent ID."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag = await create_tag(db_session, name="Test", agent_id="agent-1")
        await db_session.commit()

        fetched = await get_tag(db_session, tag.id, "agent-2")

    assert fetched is None


@pytest.mark.docker
async def test_get_tag_by_name(
    db_session: AsyncSession, mock_generate_embedding: AsyncMock
) -> None:
    """Get a tag by canonical name."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag = await create_tag(db_session, name="Machine Learning", agent_id="test-agent")
        await db_session.commit()

        # Should find with exact match
        fetched = await get_tag_by_name(db_session, "Machine Learning", "test-agent")
        assert fetched is not None
        assert fetched.id == tag.id

        # Should find with different case
        fetched = await get_tag_by_name(db_session, "machine learning", "test-agent")
        assert fetched is not None
        assert fetched.id == tag.id


@pytest.mark.docker
async def test_list_tags(db_session: AsyncSession, mock_generate_embedding: AsyncMock) -> None:
    """List all tags for an agent."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        await create_tag(db_session, name="Python", agent_id="test-agent")
        await create_tag(db_session, name="ML", agent_id="test-agent")
        await create_tag(db_session, name="Other", agent_id="other-agent")
        await db_session.commit()

        tags = await list_tags(db_session, "test-agent")

    assert len(tags) == 2
    names = {t.name for t in tags}
    assert names == {"Python", "ML"}


@pytest.mark.docker
async def test_list_tags_pagination(
    db_session: AsyncSession, mock_generate_embedding: AsyncMock
) -> None:
    """List tags with pagination."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        for i in range(5):
            await create_tag(db_session, name=f"Tag{i}", agent_id="test-agent")
        await db_session.commit()

        page1 = await list_tags(db_session, "test-agent", limit=2, offset=0)
        page2 = await list_tags(db_session, "test-agent", limit=2, offset=2)

    assert len(page1) == 2
    assert len(page2) == 2


@pytest.mark.docker
async def test_update_tag(db_session: AsyncSession, mock_generate_embedding: AsyncMock) -> None:
    """Update a tag's name and description."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag = await create_tag(db_session, name="Old", agent_id="test-agent")
        await db_session.commit()

        updated = await update_tag(
            db_session, tag.id, "test-agent", name="New", description="Updated desc"
        )
        await db_session.commit()

    assert updated is not None
    assert updated.name == "New"
    assert updated.canonical_key == "new"
    assert updated.description == "Updated desc"


@pytest.mark.docker
async def test_delete_tag(db_session: AsyncSession, mock_generate_embedding: AsyncMock) -> None:
    """Delete a tag."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag = await create_tag(db_session, name="ToDelete", agent_id="test-agent")
        await db_session.commit()

        deleted = await delete_tag(db_session, tag.id, "test-agent")
        await db_session.commit()

    assert deleted is True

    fetched = await get_tag(db_session, tag.id, "test-agent")
    assert fetched is None


@pytest.mark.docker
async def test_delete_nonexistent_tag(db_session: AsyncSession) -> None:
    """Deleting nonexistent tag returns False."""
    deleted = await delete_tag(db_session, uuid4(), "test-agent")
    assert deleted is False


@pytest.mark.docker
async def test_count_tags(db_session: AsyncSession, mock_generate_embedding: AsyncMock) -> None:
    """Count tags for an agent."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        await create_tag(db_session, name="Tag1", agent_id="test-agent")
        await create_tag(db_session, name="Tag2", agent_id="test-agent")
        await create_tag(db_session, name="Other", agent_id="other-agent")
        await db_session.commit()

        count = await count_tags(db_session, "test-agent")

    assert count == 2


# =============================================================================
# Passage-tag relationship tests
# =============================================================================


@pytest.mark.docker
async def test_attach_tag_to_passage(
    db_session: AsyncSession, sample_passage: Passage, mock_generate_embedding: AsyncMock
) -> None:
    """Attach a tag to a passage."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag = await create_tag(db_session, name="Python", agent_id="test-agent")
        await db_session.commit()

        attached = await attach_tag_to_passage(db_session, sample_passage.id, tag.id, "test-agent")
        await db_session.commit()
        await db_session.refresh(tag)

    assert attached is True
    assert tag.passage_count == 1


@pytest.mark.docker
async def test_attach_tag_idempotent(
    db_session: AsyncSession, sample_passage: Passage, mock_generate_embedding: AsyncMock
) -> None:
    """Attaching same tag twice doesn't create duplicate."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag = await create_tag(db_session, name="Python", agent_id="test-agent")
        await db_session.commit()

        await attach_tag_to_passage(db_session, sample_passage.id, tag.id, "test-agent")
        await db_session.commit()

        # Second attach should return False
        attached = await attach_tag_to_passage(db_session, sample_passage.id, tag.id, "test-agent")

    assert attached is False


@pytest.mark.docker
async def test_attach_tags_to_passage(
    db_session: AsyncSession, sample_passage: Passage, mock_generate_embedding: AsyncMock
) -> None:
    """Attach multiple tags to a passage."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag1 = await create_tag(db_session, name="Python", agent_id="test-agent")
        tag2 = await create_tag(db_session, name="ML", agent_id="test-agent")
        await db_session.commit()

        count = await attach_tags_to_passage(
            db_session, sample_passage.id, [tag1.id, tag2.id], "test-agent"
        )
        await db_session.commit()

    assert count == 2


@pytest.mark.docker
async def test_detach_tag_from_passage(
    db_session: AsyncSession, sample_passage: Passage, mock_generate_embedding: AsyncMock
) -> None:
    """Detach a tag from a passage."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag = await create_tag(db_session, name="Python", agent_id="test-agent")
        await db_session.commit()

        await attach_tag_to_passage(db_session, sample_passage.id, tag.id, "test-agent")
        await db_session.commit()

        detached = await detach_tag_from_passage(
            db_session, sample_passage.id, tag.id, "test-agent"
        )
        await db_session.commit()
        await db_session.refresh(tag)

    assert detached is True
    assert tag.passage_count == 0


@pytest.mark.docker
async def test_detach_nonexistent_tag(db_session: AsyncSession, sample_passage: Passage) -> None:
    """Detaching non-attached tag returns False."""
    detached = await detach_tag_from_passage(db_session, sample_passage.id, uuid4(), "test-agent")
    assert detached is False


@pytest.mark.docker
async def test_get_passage_tags(
    db_session: AsyncSession, sample_passage: Passage, mock_generate_embedding: AsyncMock
) -> None:
    """Get all tags for a passage."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag1 = await create_tag(db_session, name="Python", agent_id="test-agent")
        tag2 = await create_tag(db_session, name="ML", agent_id="test-agent")
        await db_session.commit()

        await attach_tag_to_passage(db_session, sample_passage.id, tag1.id, "test-agent")
        await attach_tag_to_passage(db_session, sample_passage.id, tag2.id, "test-agent")
        await db_session.commit()

        tags = await get_passage_tags(db_session, sample_passage.id, "test-agent")

    assert len(tags) == 2
    names = {t.name for t in tags}
    assert names == {"Python", "ML"}


@pytest.mark.docker
async def test_get_passages_by_tag(
    db_session: AsyncSession,
    sample_passage: Passage,
    another_passage: Passage,
    mock_generate_embedding: AsyncMock,
) -> None:
    """Get all passages with a specific tag."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag = await create_tag(db_session, name="Python", agent_id="test-agent")
        await db_session.commit()

        await attach_tag_to_passage(db_session, sample_passage.id, tag.id, "test-agent")
        await attach_tag_to_passage(db_session, another_passage.id, tag.id, "test-agent")
        await db_session.commit()

        passages = await get_passages_by_tag(db_session, tag.id, "test-agent")

    assert len(passages) == 2


@pytest.mark.docker
async def test_delete_tag_cascades_to_passage_tags(
    db_session: AsyncSession, sample_passage: Passage, mock_generate_embedding: AsyncMock
) -> None:
    """Deleting a tag removes it from all passages."""
    with patch("kp3.services.tags.generate_embedding", mock_generate_embedding):
        tag = await create_tag(db_session, name="ToDelete", agent_id="test-agent")
        await db_session.commit()

        await attach_tag_to_passage(db_session, sample_passage.id, tag.id, "test-agent")
        await db_session.commit()

        await delete_tag(db_session, tag.id, "test-agent")
        await db_session.commit()

        tags = await get_passage_tags(db_session, sample_passage.id, "test-agent")

    assert len(tags) == 0


# =============================================================================
# Search tests (require full stack)
# =============================================================================
# Note: Full search tests would require OpenAI embeddings.
# These are integration-level tests that verify SQL queries work.


@pytest.mark.docker
async def test_search_content_with_timestamp_filter(
    db_session: AsyncSession, passage_with_dates: Passage
) -> None:
    """Content search can filter by timestamps."""
    from kp3.services.search import _build_timestamp_filters

    now = datetime.now(timezone.utc)

    # Build filters for "created in the last week"
    filters, params = _build_timestamp_filters(
        created_after=now - timedelta(days=7),
    )

    assert "p.created_at >= :created_after" in filters
    assert "created_after" in params


@pytest.mark.docker
async def test_search_content_with_period_filter(db_session: AsyncSession) -> None:
    """Content search can filter by period dates."""
    from kp3.services.search import _build_timestamp_filters

    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 1, 31, tzinfo=timezone.utc)

    filters, _params = _build_timestamp_filters(
        period_start_after=start,
        period_end_before=end,
    )

    assert "p.period_start >= :period_start_after" in filters
    assert "p.period_end <= :period_end_before" in filters
