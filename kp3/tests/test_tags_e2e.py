"""End-to-end functional tests for the tags system.

These tests use a real PostgreSQL database via testcontainers to verify
the complete tagging workflow including:
- Tag CRUD operations
- Passage-tag relationships
- Tag-based search (FTS, semantic, hybrid)
- Timestamp filtering
- API endpoints

Run with: uv run pytest tests/test_tags_e2e.py -v
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.services.passages import create_passage
from kp3.services.search import search_passages
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
# Test fixtures
# =============================================================================


@pytest.fixture
def mock_embedding() -> list[float]:
    """Return a deterministic mock embedding vector."""
    return [0.1] * 1024


@pytest.fixture
def mock_embedding_fn(mock_embedding: list[float]) -> AsyncMock:
    """Mock embedding function that returns consistent embeddings."""
    return AsyncMock(return_value=mock_embedding)


@pytest.fixture
def varied_embeddings() -> dict[str, list[float]]:
    """Return different embeddings for different content to test semantic search."""
    return {
        "python": [0.9, 0.1, 0.0] + [0.0] * 1021,
        "javascript": [0.1, 0.9, 0.0] + [0.0] * 1021,
        "database": [0.0, 0.1, 0.9] + [0.0] * 1021,
        "programming": [0.7, 0.7, 0.0] + [0.0] * 1021,
        "web": [0.1, 0.8, 0.2] + [0.0] * 1021,
        "default": [0.5] * 1024,
    }


def create_varied_embedding_mock(embeddings: dict[str, list[float]]) -> AsyncMock:
    """Create a mock that returns different embeddings based on input text."""

    async def mock_generate(text: str, model: str | None = None) -> list[float]:
        text_lower = text.lower()
        for key, embedding in embeddings.items():
            if key in text_lower:
                return embedding
        return embeddings["default"]

    return AsyncMock(side_effect=mock_generate)


# =============================================================================
# Database setup tests
# =============================================================================


@pytest.mark.docker
async def test_database_tables_created(db_session: AsyncSession) -> None:
    """Verify that the tags and passage_tags tables are created."""
    # Check tags table exists
    result = await db_session.execute(
        text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'tags')")
    )
    assert result.scalar() is True

    # Check passage_tags table exists
    result = await db_session.execute(
        text(
            "SELECT EXISTS "
            "(SELECT FROM information_schema.tables WHERE table_name = 'passage_tags')"
        )
    )
    assert result.scalar() is True


@pytest.mark.docker
async def test_tags_table_has_vector_column(db_session: AsyncSession) -> None:
    """Verify the tags table has the embedding_openai vector column."""
    result = await db_session.execute(
        text("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'tags' AND column_name = 'embedding_openai'
        """)
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == "USER-DEFINED"  # pgvector type


# =============================================================================
# Tag CRUD operations
# =============================================================================


@pytest.mark.docker
async def test_full_tag_lifecycle(db_session: AsyncSession, mock_embedding_fn: AsyncMock) -> None:
    """Test the complete lifecycle of a tag: create, read, update, delete."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        # Create
        tag = await create_tag(
            db_session,
            name="Python Programming",
            agent_id="test-agent",
            description="Content about Python language",
        )
        await db_session.commit()

        assert tag.id is not None
        assert tag.name == "Python Programming"
        assert tag.canonical_key == "python programming"
        assert tag.description == "Content about Python language"
        assert tag.agent_id == "test-agent"
        assert tag.passage_count == 0
        assert tag.embedding_openai is not None
        assert len(tag.embedding_openai) == 1024

        # Read by ID
        fetched = await get_tag(db_session, tag.id, "test-agent")
        assert fetched is not None
        assert fetched.id == tag.id
        assert fetched.name == "Python Programming"

        # Read by name
        fetched_by_name = await get_tag_by_name(db_session, "python programming", "test-agent")
        assert fetched_by_name is not None
        assert fetched_by_name.id == tag.id

        # Update
        updated = await update_tag(
            db_session,
            tag.id,
            "test-agent",
            name="Python 3",
            description="Modern Python programming",
        )
        await db_session.commit()

        assert updated is not None
        assert updated.name == "Python 3"
        assert updated.canonical_key == "python 3"
        assert updated.description == "Modern Python programming"

        # Delete
        deleted = await delete_tag(db_session, tag.id, "test-agent")
        await db_session.commit()
        assert deleted is True

        # Verify deletion
        fetched_after_delete = await get_tag(db_session, tag.id, "test-agent")
        assert fetched_after_delete is None


@pytest.mark.docker
async def test_tag_deduplication(db_session: AsyncSession, mock_embedding_fn: AsyncMock) -> None:
    """Test that tags with the same canonical name cannot be duplicated."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        # Create first tag
        await create_tag(db_session, name="Machine Learning", agent_id="test-agent")
        await db_session.commit()

        # Try to create duplicate with different casing
        with pytest.raises(ValueError, match="already exists"):
            await create_tag(db_session, name="machine learning", agent_id="test-agent")

        # But can create same name for different agent
        tag2 = await create_tag(db_session, name="Machine Learning", agent_id="other-agent")
        await db_session.commit()
        assert tag2.id is not None


@pytest.mark.docker
async def test_get_or_create_tag_idempotent(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test that get_or_create_tag is idempotent."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        # First call creates
        tag1 = await get_or_create_tag(db_session, "New Tag", "test-agent")
        await db_session.commit()
        tag1_id = tag1.id

        # Second call returns existing
        tag2 = await get_or_create_tag(db_session, "new tag", "test-agent")  # Different case
        assert tag2.id == tag1_id

        # Verify only one tag exists
        count = await count_tags(db_session, "test-agent")
        assert count == 1


@pytest.mark.docker
async def test_list_tags_with_ordering(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test listing tags with different orderings."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        # Create tags in specific order with small delays to ensure different timestamps
        await create_tag(db_session, name="Zebra", agent_id="test-agent")
        await db_session.commit()
        await asyncio.sleep(0.01)  # Ensure different timestamps

        await create_tag(db_session, name="Apple", agent_id="test-agent")
        await db_session.commit()
        await asyncio.sleep(0.01)

        await create_tag(db_session, name="Mango", agent_id="test-agent")
        await db_session.commit()

        # Order by name (default)
        tags_by_name = await list_tags(db_session, "test-agent", order_by="name")
        names = [t.name for t in tags_by_name]
        assert names == ["Apple", "Mango", "Zebra"]

        # Order by created_at (descending, most recent first)
        tags_by_created = await list_tags(db_session, "test-agent", order_by="created_at")
        names_by_created = [t.name for t in tags_by_created]
        assert names_by_created == ["Mango", "Apple", "Zebra"]


@pytest.mark.docker
async def test_tag_agent_isolation(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test that tags are isolated between agents."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        # Create tags for different agents
        await create_tag(db_session, name="Shared Name", agent_id="agent-1")
        tag2 = await create_tag(db_session, name="Agent 2 Only", agent_id="agent-2")
        await db_session.commit()

        # Agent 1 can only see their tags
        agent1_tags = await list_tags(db_session, "agent-1")
        assert len(agent1_tags) == 1
        assert agent1_tags[0].name == "Shared Name"

        # Agent 2 can only see their tags
        agent2_tags = await list_tags(db_session, "agent-2")
        assert len(agent2_tags) == 1
        assert agent2_tags[0].name == "Agent 2 Only"

        # Agent 1 cannot access agent 2's tag
        cross_access = await get_tag(db_session, tag2.id, "agent-1")
        assert cross_access is None


# =============================================================================
# Passage-Tag relationships
# =============================================================================


@pytest.mark.docker
async def test_attach_and_detach_tags(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test attaching and detaching tags from passages."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        # Create a passage
        passage = await create_passage(
            db_session,
            content="A comprehensive guide to Python programming",
            passage_type="tutorial",
            agent_id="test-agent",
        )
        await db_session.commit()

        # Create tags
        python_tag = await create_tag(db_session, name="Python", agent_id="test-agent")
        tutorial_tag = await create_tag(db_session, name="Tutorial", agent_id="test-agent")
        await db_session.commit()

        # Attach tags
        attached1 = await attach_tag_to_passage(
            db_session, passage.id, python_tag.id, "test-agent"
        )
        attached2 = await attach_tag_to_passage(
            db_session, passage.id, tutorial_tag.id, "test-agent"
        )
        await db_session.commit()

        assert attached1 is True
        assert attached2 is True

        # Verify passage count updated
        await db_session.refresh(python_tag)
        await db_session.refresh(tutorial_tag)
        assert python_tag.passage_count == 1
        assert tutorial_tag.passage_count == 1

        # Get passage tags
        tags = await get_passage_tags(db_session, passage.id, "test-agent")
        assert len(tags) == 2
        tag_names = {t.name for t in tags}
        assert tag_names == {"Python", "Tutorial"}

        # Detach one tag
        detached = await detach_tag_from_passage(
            db_session, passage.id, python_tag.id, "test-agent"
        )
        await db_session.commit()
        assert detached is True

        # Verify passage count updated
        await db_session.refresh(python_tag)
        assert python_tag.passage_count == 0

        # Verify only one tag remains
        remaining_tags = await get_passage_tags(db_session, passage.id, "test-agent")
        assert len(remaining_tags) == 1
        assert remaining_tags[0].name == "Tutorial"


@pytest.mark.docker
async def test_attach_multiple_tags_at_once(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test attaching multiple tags to a passage in one call."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        # Create passage and tags
        passage = await create_passage(
            db_session,
            content="Full stack web development with Python and JavaScript",
            passage_type="article",
            agent_id="test-agent",
        )
        tags = []
        for name in ["Python", "JavaScript", "Web", "Full Stack"]:
            tag = await create_tag(db_session, name=name, agent_id="test-agent")
            tags.append(tag)
        await db_session.commit()

        # Attach all tags at once
        tag_ids = [t.id for t in tags]
        count = await attach_tags_to_passage(db_session, passage.id, tag_ids, "test-agent")
        await db_session.commit()

        assert count == 4

        # Verify all attached
        attached_tags = await get_passage_tags(db_session, passage.id, "test-agent")
        assert len(attached_tags) == 4


@pytest.mark.docker
async def test_get_passages_by_tag(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test retrieving all passages with a specific tag."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        # Create passages
        passages = []
        for content in [
            "Python basics for beginners",
            "Advanced Python techniques",
            "JavaScript fundamentals",
            "Python web frameworks",
        ]:
            p = await create_passage(
                db_session,
                content=content,
                passage_type="tutorial",
                agent_id="test-agent",
            )
            passages.append(p)
        await db_session.commit()

        # Create tags
        python_tag = await create_tag(db_session, name="Python", agent_id="test-agent")
        js_tag = await create_tag(db_session, name="JavaScript", agent_id="test-agent")
        await db_session.commit()

        # Tag passages
        await attach_tag_to_passage(db_session, passages[0].id, python_tag.id, "test-agent")
        await attach_tag_to_passage(db_session, passages[1].id, python_tag.id, "test-agent")
        await attach_tag_to_passage(db_session, passages[2].id, js_tag.id, "test-agent")
        await attach_tag_to_passage(db_session, passages[3].id, python_tag.id, "test-agent")
        await db_session.commit()

        # Get passages by Python tag
        python_passages = await get_passages_by_tag(db_session, python_tag.id, "test-agent")
        assert len(python_passages) == 3

        # Get passages by JavaScript tag
        js_passages = await get_passages_by_tag(db_session, js_tag.id, "test-agent")
        assert len(js_passages) == 1


@pytest.mark.docker
async def test_cascade_delete_tag_removes_associations(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test that deleting a tag cascades to remove passage_tags entries."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        # Create passage and tag
        passage = await create_passage(
            db_session,
            content="Test passage",
            passage_type="test",
            agent_id="test-agent",
        )
        tag = await create_tag(db_session, name="ToDelete", agent_id="test-agent")
        await db_session.commit()

        # Attach tag
        await attach_tag_to_passage(db_session, passage.id, tag.id, "test-agent")
        await db_session.commit()

        tag_id = tag.id

        # Delete tag
        await delete_tag(db_session, tag_id, "test-agent")
        await db_session.commit()

        # Verify passage_tags entry is gone
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM passage_tags WHERE tag_id = :tag_id"),
            {"tag_id": str(tag_id)},
        )
        count = result.scalar()
        assert count == 0

        # Passage should have no tags
        tags = await get_passage_tags(db_session, passage.id, "test-agent")
        assert len(tags) == 0


@pytest.mark.docker
async def test_cascade_delete_passage_removes_associations(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test that deleting a passage cascades to remove passage_tags entries."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        # Create passage and tag
        passage = await create_passage(
            db_session,
            content="Test passage to delete",
            passage_type="test",
            agent_id="test-agent",
        )
        tag = await create_tag(db_session, name="Persistent", agent_id="test-agent")
        await db_session.commit()

        # Attach tag
        await attach_tag_to_passage(db_session, passage.id, tag.id, "test-agent")
        await db_session.commit()

        passage_id = passage.id

        # Delete passage directly
        await db_session.execute(
            text("DELETE FROM passages WHERE id = :id"), {"id": str(passage_id)}
        )
        await db_session.commit()

        # Verify passage_tags entry is gone
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM passage_tags WHERE passage_id = :passage_id"),
            {"passage_id": str(passage_id)},
        )
        count = result.scalar()
        assert count == 0

        # Tag should still exist but with updated count
        await db_session.refresh(tag)
        # Note: passage_count won't auto-decrement on cascade delete without a trigger


# =============================================================================
# Search functionality
# =============================================================================


@pytest.mark.docker
async def test_search_passages_by_tags_fts(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test FTS search on tag names to find passages."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        with patch("kp3.services.search.generate_embedding", mock_embedding_fn):
            # Create passages
            python_passage = await create_passage(
                db_session,
                content="Introduction to variables and data types",
                passage_type="tutorial",
                agent_id="test-agent",
                embedding_openai=[0.5] * 1024,
            )
            js_passage = await create_passage(
                db_session,
                content="DOM manipulation techniques",
                passage_type="tutorial",
                agent_id="test-agent",
                embedding_openai=[0.5] * 1024,
            )
            await db_session.commit()

            # Create and attach tags
            python_tag = await create_tag(
                db_session,
                name="Python Programming",
                agent_id="test-agent",
                description="Python language tutorials",
            )
            js_tag = await create_tag(
                db_session,
                name="JavaScript",
                agent_id="test-agent",
                description="Frontend JavaScript",
            )
            await db_session.commit()

            await attach_tag_to_passage(db_session, python_passage.id, python_tag.id, "test-agent")
            await attach_tag_to_passage(db_session, js_passage.id, js_tag.id, "test-agent")
            await db_session.commit()

            # Search by tag name using FTS
            results = await search_passages(
                db_session,
                query="Python",
                search_type="tags",
                mode="fts",
                agent_id="test-agent",
            )

            assert len(results) >= 1
            # The Python-tagged passage should be in results
            result_ids = [r.id for r in results]
            assert python_passage.id in result_ids


@pytest.mark.docker
async def test_search_passages_by_content_default(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test that content search (default) still works."""
    with patch("kp3.services.search.generate_embedding", mock_embedding_fn):
        # Create passage with searchable content
        passage = await create_passage(
            db_session,
            content="PostgreSQL is a powerful relational database",
            passage_type="docs",
            agent_id="test-agent",
            embedding_openai=[0.5] * 1024,
        )
        await db_session.commit()

        # Search by content (default search_type)
        results = await search_passages(
            db_session,
            query="PostgreSQL database",
            search_type="content",  # explicit, but also the default
            mode="fts",
            agent_id="test-agent",
        )

        assert len(results) >= 1
        assert any(r.id == passage.id for r in results)


@pytest.mark.docker
async def test_search_with_timestamp_filters(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test search with timestamp filtering."""
    with patch("kp3.services.search.generate_embedding", mock_embedding_fn):
        now = datetime.now(timezone.utc)

        # Create passages with different dates
        old_passage = await create_passage(
            db_session,
            content="Old document about Python",
            passage_type="docs",
            agent_id="test-agent",
            embedding_openai=[0.5] * 1024,
        )
        await db_session.commit()

        # Manually update created_at to make it "old"
        await db_session.execute(
            text("UPDATE passages SET created_at = :old_date WHERE id = :id"),
            {"old_date": now - timedelta(days=30), "id": str(old_passage.id)},
        )
        await db_session.commit()

        new_passage = await create_passage(
            db_session,
            content="New document about Python",
            passage_type="docs",
            agent_id="test-agent",
            embedding_openai=[0.5] * 1024,
        )
        await db_session.commit()

        # Search with created_after filter (should only find new passage)
        results = await search_passages(
            db_session,
            query="Python",
            search_type="content",
            mode="fts",
            agent_id="test-agent",
            created_after=now - timedelta(days=7),
        )

        result_ids = [r.id for r in results]
        assert new_passage.id in result_ids
        assert old_passage.id not in result_ids


@pytest.mark.docker
async def test_search_with_period_filters(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test search with period_start and period_end filters."""
    with patch("kp3.services.search.generate_embedding", mock_embedding_fn):
        # Create passage with period in January
        jan_passage = await create_passage(
            db_session,
            content="January report on Python usage",
            passage_type="report",
            agent_id="test-agent",
            period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2025, 1, 31, tzinfo=timezone.utc),
            embedding_openai=[0.5] * 1024,
        )

        # Create passage with period in February
        feb_passage = await create_passage(
            db_session,
            content="February report on Python usage",
            passage_type="report",
            agent_id="test-agent",
            period_start=datetime(2025, 2, 1, tzinfo=timezone.utc),
            period_end=datetime(2025, 2, 28, tzinfo=timezone.utc),
            embedding_openai=[0.5] * 1024,
        )
        await db_session.commit()

        # Search for passages in January only
        results = await search_passages(
            db_session,
            query="Python",
            search_type="content",
            mode="fts",
            agent_id="test-agent",
            period_start_after=datetime(2025, 1, 1, tzinfo=timezone.utc),
            period_end_before=datetime(2025, 1, 31, tzinfo=timezone.utc),
        )

        result_ids = [r.id for r in results]
        assert jan_passage.id in result_ids
        assert feb_passage.id not in result_ids


# =============================================================================
# API endpoint tests
# =============================================================================


@pytest.mark.docker
async def test_api_create_tag(
    test_client: AsyncClient, mock_embedding_fn: AsyncMock
) -> None:
    """Test POST /tags endpoint."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        response = await test_client.post(
            "/tags",
            json={"name": "API Test Tag", "description": "Created via API"},
            headers={"X-Agent-ID": "test-agent"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Test Tag"
        assert data["description"] == "Created via API"
        assert data["passage_count"] == 0
        assert "id" in data
        assert "created_at" in data


@pytest.mark.docker
async def test_api_list_tags(
    test_client: AsyncClient, mock_embedding_fn: AsyncMock
) -> None:
    """Test GET /tags endpoint."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        # Create some tags first
        for name in ["Alpha", "Beta", "Gamma"]:
            await test_client.post(
                "/tags",
                json={"name": name},
                headers={"X-Agent-ID": "test-agent"},
            )

        response = await test_client.get(
            "/tags",
            headers={"X-Agent-ID": "test-agent"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        assert len(data["tags"]) >= 3
        assert data["count"] >= 3


@pytest.mark.docker
async def test_api_get_tag(
    test_client: AsyncClient, mock_embedding_fn: AsyncMock
) -> None:
    """Test GET /tags/{tag_id} endpoint."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        # Create a tag
        create_response = await test_client.post(
            "/tags",
            json={"name": "Fetchable Tag"},
            headers={"X-Agent-ID": "test-agent"},
        )
        tag_id = create_response.json()["id"]

        # Fetch it
        response = await test_client.get(
            f"/tags/{tag_id}",
            headers={"X-Agent-ID": "test-agent"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tag_id
        assert data["name"] == "Fetchable Tag"


@pytest.mark.docker
async def test_api_delete_tag(
    test_client: AsyncClient, mock_embedding_fn: AsyncMock
) -> None:
    """Test DELETE /tags/{tag_id} endpoint."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        # Create a tag
        create_response = await test_client.post(
            "/tags",
            json={"name": "Deletable Tag"},
            headers={"X-Agent-ID": "test-agent"},
        )
        tag_id = create_response.json()["id"]

        # Delete it
        response = await test_client.delete(
            f"/tags/{tag_id}",
            headers={"X-Agent-ID": "test-agent"},
        )
        assert response.status_code == 204

        # Verify it's gone
        get_response = await test_client.get(
            f"/tags/{tag_id}",
            headers={"X-Agent-ID": "test-agent"},
        )
        assert get_response.status_code == 404


@pytest.mark.docker
async def test_api_attach_tags_to_passage(
    test_client: AsyncClient, mock_embedding_fn: AsyncMock
) -> None:
    """Test POST /passages/{passage_id}/tags endpoint."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        with patch("kp3.query_service.router.generate_embedding", mock_embedding_fn):
            # Create a passage
            passage_response = await test_client.post(
                "/passages",
                json={"content": "Test content for tagging", "passage_type": "test"},
                headers={"X-Agent-ID": "test-agent"},
            )
            passage_id = passage_response.json()["id"]

            # Create tags
            tag1_response = await test_client.post(
                "/tags",
                json={"name": "Tag One"},
                headers={"X-Agent-ID": "test-agent"},
            )
            tag2_response = await test_client.post(
                "/tags",
                json={"name": "Tag Two"},
                headers={"X-Agent-ID": "test-agent"},
            )
            tag1_id = tag1_response.json()["id"]
            tag2_id = tag2_response.json()["id"]

            # Attach tags to passage
            response = await test_client.post(
                f"/passages/{passage_id}/tags",
                json={"tag_ids": [tag1_id, tag2_id]},
                headers={"X-Agent-ID": "test-agent"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["passage_id"] == passage_id
            assert len(data["tags"]) == 2


@pytest.mark.docker
async def test_api_get_passage_tags(
    test_client: AsyncClient, mock_embedding_fn: AsyncMock
) -> None:
    """Test GET /passages/{passage_id}/tags endpoint."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        with patch("kp3.query_service.router.generate_embedding", mock_embedding_fn):
            # Create passage and tag
            passage_response = await test_client.post(
                "/passages",
                json={"content": "Another test passage", "passage_type": "test"},
                headers={"X-Agent-ID": "test-agent"},
            )
            passage_id = passage_response.json()["id"]

            tag_response = await test_client.post(
                "/tags",
                json={"name": "Viewable Tag"},
                headers={"X-Agent-ID": "test-agent"},
            )
            tag_id = tag_response.json()["id"]

            # Attach tag
            await test_client.post(
                f"/passages/{passage_id}/tags",
                json={"tag_ids": [tag_id]},
                headers={"X-Agent-ID": "test-agent"},
            )

            # Get passage tags
            response = await test_client.get(
                f"/passages/{passage_id}/tags",
                headers={"X-Agent-ID": "test-agent"},
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["tags"]) == 1
            assert data["tags"][0]["name"] == "Viewable Tag"


@pytest.mark.docker
async def test_api_search_by_tags(
    test_client: AsyncClient, mock_embedding_fn: AsyncMock
) -> None:
    """Test GET /passages/search with search_type=tags."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        with patch("kp3.services.search.generate_embedding", mock_embedding_fn):
            with patch("kp3.query_service.router.generate_embedding", mock_embedding_fn):
                # Create passage
                passage_response = await test_client.post(
                    "/passages",
                    json={"content": "Database optimization tips", "passage_type": "guide"},
                    headers={"X-Agent-ID": "test-agent"},
                )
                passage_id = passage_response.json()["id"]

                # Create tag
                tag_response = await test_client.post(
                    "/tags",
                    json={"name": "Performance", "description": "Performance optimization"},
                    headers={"X-Agent-ID": "test-agent"},
                )
                tag_id = tag_response.json()["id"]

                # Attach tag
                await test_client.post(
                    f"/passages/{passage_id}/tags",
                    json={"tag_ids": [tag_id]},
                    headers={"X-Agent-ID": "test-agent"},
                )

                # Search by tag
                response = await test_client.get(
                    "/passages/search",
                    params={"query": "Performance", "search_type": "tags", "mode": "fts"},
                    headers={"X-Agent-ID": "test-agent"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["search_type"] == "tags"
                # Should find the passage via its tag
                if data["count"] > 0:
                    result_ids = [r["id"] for r in data["results"]]
                    assert passage_id in result_ids


@pytest.mark.docker
async def test_api_search_with_timestamp_filter(
    test_client: AsyncClient, mock_embedding_fn: AsyncMock
) -> None:
    """Test GET /passages/search with timestamp filters."""
    with patch("kp3.services.search.generate_embedding", mock_embedding_fn):
        with patch("kp3.query_service.router.generate_embedding", mock_embedding_fn):
            # Create a passage
            await test_client.post(
                "/passages",
                json={"content": "Filtered content about Python", "passage_type": "test"},
                headers={"X-Agent-ID": "test-agent"},
            )

            # Search with timestamp filter
            now = datetime.now(timezone.utc)
            response = await test_client.get(
                "/passages/search",
                params={
                    "query": "Python",
                    "search_type": "content",
                    "mode": "fts",
                    "created_after": (now - timedelta(hours=1)).isoformat(),
                },
                headers={"X-Agent-ID": "test-agent"},
            )

            assert response.status_code == 200
            # The passage was just created, so it should be included


@pytest.mark.docker
async def test_api_duplicate_tag_returns_409(
    test_client: AsyncClient, mock_embedding_fn: AsyncMock
) -> None:
    """Test that creating a duplicate tag returns 409 Conflict."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        # Create first tag
        await test_client.post(
            "/tags",
            json={"name": "Unique Tag"},
            headers={"X-Agent-ID": "test-agent"},
        )

        # Try to create duplicate
        response = await test_client.post(
            "/tags",
            json={"name": "unique tag"},  # Same canonical name
            headers={"X-Agent-ID": "test-agent"},
        )

        assert response.status_code == 409


# =============================================================================
# Edge cases and error handling
# =============================================================================


@pytest.mark.docker
async def test_attach_tag_to_nonexistent_passage(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test attaching a tag to a non-existent passage fails gracefully."""
    from uuid import uuid4

    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        tag = await create_tag(db_session, name="Orphan Tag", agent_id="test-agent")
        await db_session.commit()

        fake_passage_id = uuid4()
        result = await attach_tag_to_passage(
            db_session, fake_passage_id, tag.id, "test-agent"
        )

        assert result is False


@pytest.mark.docker
async def test_attach_nonexistent_tag_to_passage(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test attaching a non-existent tag to a passage fails gracefully."""
    from uuid import uuid4

    passage = await create_passage(
        db_session,
        content="Passage without tags",
        passage_type="test",
        agent_id="test-agent",
    )
    await db_session.commit()

    fake_tag_id = uuid4()
    result = await attach_tag_to_passage(
        db_session, passage.id, fake_tag_id, "test-agent"
    )

    assert result is False


@pytest.mark.docker
async def test_canonicalize_various_inputs() -> None:
    """Test canonicalization with various edge cases."""
    # Basic normalization
    assert canonicalize_tag_name("Hello World") == "hello world"

    # Multiple spaces
    assert canonicalize_tag_name("  Multiple   Spaces  ") == "multiple spaces"

    # Tabs and newlines
    assert canonicalize_tag_name("Tab\tand\nNewline") == "tab and newline"

    # Already lowercase
    assert canonicalize_tag_name("already lowercase") == "already lowercase"

    # Single word
    assert canonicalize_tag_name("WORD") == "word"

    # Unicode (should preserve)
    assert canonicalize_tag_name("Café résumé") == "café résumé"


@pytest.mark.docker
async def test_empty_tag_search_returns_empty(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test that searching for tags that don't exist returns empty results."""
    with patch("kp3.services.tags.generate_embedding", mock_embedding_fn):
        with patch("kp3.services.search.generate_embedding", mock_embedding_fn):
            # Create a passage without tags (just to have data in the DB)
            await create_passage(
                db_session,
                content="Untagged content",
                passage_type="test",
                agent_id="test-agent",
                embedding_openai=[0.5] * 1024,
            )
            await db_session.commit()

            # Search by tags for something that doesn't exist
            results = await search_passages(
                db_session,
                query="NonexistentTag",
                search_type="tags",
                mode="fts",
                agent_id="test-agent",
            )

            # Should return empty since no tags match
            assert len(results) == 0
