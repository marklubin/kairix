"""End-to-end functional tests for the Memory Scopes system.

These tests use a real PostgreSQL database via testcontainers to verify
the complete scopes workflow including:
- Scope CRUD operations
- Scope definitions stored as passages
- Scoped passage operations
- Scoped search
- History and revert functionality
- API endpoints

Run with: uv run pytest tests/test_scopes_e2e.py -v
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.services.passages import create_passage
from kp3.services.refs import set_ref
from kp3.services.scopes import (
    SCOPE_DEFINITION_TYPE,
    add_passages_to_scope,
    add_refs_to_scope,
    create_passage_in_scope,
    create_scope,
    delete_scope,
    get_current_version,
    get_scope,
    get_scope_history,
    list_scopes,
    remove_from_scope,
    resolve_scope,
    revert_scope,
)
from kp3.services.search import search_passages

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


# =============================================================================
# Database setup tests
# =============================================================================


@pytest.mark.docker
async def test_memory_scopes_table_created(db_session: AsyncSession) -> None:
    """Verify that the memory_scopes table is created."""
    result = await db_session.execute(
        text(
            "SELECT EXISTS "
            "(SELECT FROM information_schema.tables WHERE table_name = 'memory_scopes')"
        )
    )
    assert result.scalar() is True


@pytest.mark.docker
async def test_scope_definition_stored_as_passage(db_session: AsyncSession) -> None:
    """Verify scope definitions are stored as passages with correct type."""
    await create_scope(db_session, "test-scope", "test-agent")
    await db_session.commit()

    # Check that a passage with type "scope_definition" was created
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM passages WHERE passage_type = :ptype AND agent_id = :agent_id"),
        {"ptype": SCOPE_DEFINITION_TYPE, "agent_id": "test-agent"},
    )
    count = result.scalar()
    assert count >= 1


# =============================================================================
# Scope CRUD operations
# =============================================================================


@pytest.mark.docker
async def test_create_scope(db_session: AsyncSession) -> None:
    """Test creating a new scope."""
    scope = await create_scope(
        db_session,
        name="working-memory",
        agent_id="test-agent",
        description="Active context scope",
    )
    await db_session.commit()

    assert scope.id is not None
    assert scope.name == "working-memory"
    assert scope.agent_id == "test-agent"
    assert scope.description == "Active context scope"
    assert scope.head_ref == "test-agent/scope/working-memory/HEAD"
    assert scope.created_at is not None
    assert scope.updated_at is not None


@pytest.mark.docker
async def test_create_scope_initializes_empty_definition(db_session: AsyncSession) -> None:
    """Test that a new scope has an empty definition."""
    scope = await create_scope(db_session, "empty-scope", "test-agent")
    await db_session.commit()

    # Resolve should return empty set
    scope_ids = await resolve_scope(db_session, scope)
    assert scope_ids == set()

    # Version should be 1
    version = await get_current_version(db_session, scope)
    assert version == 1


@pytest.mark.docker
async def test_create_duplicate_scope_fails(db_session: AsyncSession) -> None:
    """Test that creating a duplicate scope raises an error."""
    await create_scope(db_session, "unique-scope", "test-agent")
    await db_session.commit()

    with pytest.raises(ValueError, match="already exists"):
        await create_scope(db_session, "unique-scope", "test-agent")


@pytest.mark.docker
async def test_get_scope(db_session: AsyncSession) -> None:
    """Test retrieving a scope by name."""
    created = await create_scope(db_session, "fetchable", "test-agent")
    await db_session.commit()

    fetched = await get_scope(db_session, "fetchable", "test-agent")
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "fetchable"


@pytest.mark.docker
async def test_get_nonexistent_scope(db_session: AsyncSession) -> None:
    """Test retrieving a scope that doesn't exist."""
    result = await get_scope(db_session, "nonexistent", "test-agent")
    assert result is None


@pytest.mark.docker
async def test_list_scopes(db_session: AsyncSession) -> None:
    """Test listing scopes for an agent."""
    await create_scope(db_session, "scope-a", "test-agent")
    await create_scope(db_session, "scope-b", "test-agent")
    await create_scope(db_session, "scope-c", "test-agent")
    await db_session.commit()

    scopes = await list_scopes(db_session, "test-agent")
    names = [s.name for s in scopes]

    assert "scope-a" in names
    assert "scope-b" in names
    assert "scope-c" in names


@pytest.mark.docker
async def test_scope_agent_isolation(db_session: AsyncSession) -> None:
    """Test that scopes are isolated between agents."""
    await create_scope(db_session, "shared-name", "agent-1")
    await create_scope(db_session, "shared-name", "agent-2")
    await db_session.commit()

    # Each agent sees only their scope
    agent1_scopes = await list_scopes(db_session, "agent-1")
    agent2_scopes = await list_scopes(db_session, "agent-2")

    assert len([s for s in agent1_scopes if s.name == "shared-name"]) == 1
    assert len([s for s in agent2_scopes if s.name == "shared-name"]) == 1

    # Cross-agent access returns None
    cross = await get_scope(db_session, "shared-name", "agent-3")
    assert cross is None


@pytest.mark.docker
async def test_delete_scope(db_session: AsyncSession) -> None:
    """Test deleting a scope."""
    await create_scope(db_session, "deletable", "test-agent")
    await db_session.commit()

    deleted = await delete_scope(db_session, "deletable", "test-agent")
    await db_session.commit()
    assert deleted is True

    # Verify it's gone
    fetched = await get_scope(db_session, "deletable", "test-agent")
    assert fetched is None


@pytest.mark.docker
async def test_delete_nonexistent_scope(db_session: AsyncSession) -> None:
    """Test deleting a scope that doesn't exist."""
    deleted = await delete_scope(db_session, "nonexistent", "test-agent")
    assert deleted is False


# =============================================================================
# Scoped Operations
# =============================================================================


@pytest.mark.docker
async def test_create_passage_in_scope(db_session: AsyncSession) -> None:
    """Test creating a passage and adding it to a scope atomically."""
    scope = await create_scope(db_session, "passage-scope", "test-agent")
    await db_session.commit()

    passage, new_version = await create_passage_in_scope(
        db_session,
        scope,
        content="Important context to remember",
        passage_type="memory",
    )
    await db_session.commit()

    assert passage.id is not None
    assert passage.content == "Important context to remember"
    assert new_version == 2  # Initial was 1

    # Verify passage is in scope
    scope_ids = await resolve_scope(db_session, scope)
    assert passage.id in scope_ids


@pytest.mark.docker
async def test_create_multiple_passages_in_scope(db_session: AsyncSession) -> None:
    """Test that creating multiple passages increments version correctly."""
    scope = await create_scope(db_session, "multi-passage", "test-agent")
    await db_session.commit()

    _, v1 = await create_passage_in_scope(db_session, scope, "First", "memory")
    _, v2 = await create_passage_in_scope(db_session, scope, "Second", "memory")
    _, v3 = await create_passage_in_scope(db_session, scope, "Third", "memory")
    await db_session.commit()

    assert v1 == 2
    assert v2 == 3
    assert v3 == 4

    scope_ids = await resolve_scope(db_session, scope)
    assert len(scope_ids) == 3


@pytest.mark.docker
async def test_add_passages_to_scope(db_session: AsyncSession) -> None:
    """Test adding existing passages to a scope."""
    scope = await create_scope(db_session, "add-test", "test-agent")

    # Create passages outside the scope
    p1 = await create_passage(db_session, "Passage 1", "test", agent_id="test-agent")
    p2 = await create_passage(db_session, "Passage 2", "test", agent_id="test-agent")
    await db_session.commit()

    # Add them to scope
    new_version, added_count = await add_passages_to_scope(db_session, scope, [p1.id, p2.id])
    await db_session.commit()

    assert added_count == 2
    assert new_version == 2

    scope_ids = await resolve_scope(db_session, scope)
    assert p1.id in scope_ids
    assert p2.id in scope_ids


@pytest.mark.docker
async def test_add_nonexistent_passage_to_scope(db_session: AsyncSession) -> None:
    """Test that adding a non-existent passage is gracefully ignored."""
    scope = await create_scope(db_session, "nonexistent-test", "test-agent")
    await db_session.commit()

    fake_id = uuid4()
    new_version, added_count = await add_passages_to_scope(db_session, scope, [fake_id])
    await db_session.commit()

    assert added_count == 0
    assert new_version == 1  # No change


@pytest.mark.docker
async def test_add_refs_to_scope(db_session: AsyncSession) -> None:
    """Test adding refs to a scope."""
    scope = await create_scope(db_session, "ref-test", "test-agent")
    await db_session.commit()

    new_version, added_count = await add_refs_to_scope(
        db_session, scope, ["test-agent/human/HEAD", "test-agent/persona/HEAD"]
    )
    await db_session.commit()

    assert added_count == 2
    assert new_version == 2


@pytest.mark.docker
async def test_add_nonexistent_ref_to_scope(db_session: AsyncSession) -> None:
    """Test that adding a non-existent ref is allowed (resolved at search time)."""
    scope = await create_scope(db_session, "ref-nonexistent", "test-agent")
    await db_session.commit()

    # This should succeed - refs are validated at search time
    new_version, added_count = await add_refs_to_scope(db_session, scope, ["nonexistent/ref"])
    await db_session.commit()

    assert added_count == 1
    assert new_version == 2


@pytest.mark.docker
async def test_remove_from_scope(db_session: AsyncSession) -> None:
    """Test removing passages and refs from a scope."""
    scope = await create_scope(db_session, "remove-test", "test-agent")

    p1 = await create_passage(db_session, "To keep", "test", agent_id="test-agent")
    p2 = await create_passage(db_session, "To remove", "test", agent_id="test-agent")
    await db_session.commit()

    await add_passages_to_scope(db_session, scope, [p1.id, p2.id])
    await add_refs_to_scope(db_session, scope, ["ref1", "ref2"])
    await db_session.commit()

    # Remove one passage and one ref
    _, removed_count = await remove_from_scope(
        db_session, scope, passage_ids=[p2.id], refs=["ref1"]
    )
    await db_session.commit()

    assert removed_count == 2

    # Verify resolution
    scope_ids = await resolve_scope(db_session, scope)
    assert p1.id in scope_ids
    assert p2.id not in scope_ids


@pytest.mark.docker
async def test_scope_resolution(db_session: AsyncSession) -> None:
    """Test resolving a scope to passage IDs."""
    scope = await create_scope(db_session, "resolve-test", "test-agent")

    # Add literal passages
    p1 = await create_passage(db_session, "Direct 1", "test", agent_id="test-agent")
    p2 = await create_passage(db_session, "Direct 2", "test", agent_id="test-agent")
    await add_passages_to_scope(db_session, scope, [p1.id, p2.id])

    # Create a passage via ref
    ref_passage = await create_passage(db_session, "Via ref", "test", agent_id="test-agent")
    await set_ref(db_session, "test-agent/ref/test", ref_passage.id, fire_hooks=False)
    await add_refs_to_scope(db_session, scope, ["test-agent/ref/test"])
    await db_session.commit()

    # Resolve
    scope_ids = await resolve_scope(db_session, scope)

    assert len(scope_ids) == 3
    assert p1.id in scope_ids
    assert p2.id in scope_ids
    assert ref_passage.id in scope_ids


@pytest.mark.docker
async def test_ref_resolution_is_dynamic(db_session: AsyncSession) -> None:
    """Test that ref resolution reflects current ref target."""
    scope = await create_scope(db_session, "dynamic-ref", "test-agent")

    # Create initial passage and ref
    p1 = await create_passage(db_session, "Initial", "test", agent_id="test-agent")
    await set_ref(db_session, "test-agent/dynamic/HEAD", p1.id, fire_hooks=False)
    await add_refs_to_scope(db_session, scope, ["test-agent/dynamic/HEAD"])
    await db_session.commit()

    # Resolve shows p1
    scope_ids = await resolve_scope(db_session, scope)
    assert p1.id in scope_ids

    # Update the ref to point to a different passage
    p2 = await create_passage(db_session, "Updated", "test", agent_id="test-agent")
    await set_ref(db_session, "test-agent/dynamic/HEAD", p2.id, fire_hooks=False)
    await db_session.commit()

    # Resolve now shows p2, not p1
    scope_ids = await resolve_scope(db_session, scope)
    assert p2.id in scope_ids
    assert p1.id not in scope_ids


@pytest.mark.docker
async def test_scope_with_deleted_passage(db_session: AsyncSession) -> None:
    """Test that deleted passages are excluded from resolution."""
    scope = await create_scope(db_session, "deleted-test", "test-agent")

    p1 = await create_passage(db_session, "Keep", "test", agent_id="test-agent")
    p2 = await create_passage(db_session, "Delete", "test", agent_id="test-agent")
    await add_passages_to_scope(db_session, scope, [p1.id, p2.id])
    await db_session.commit()

    # Delete p2 directly
    await db_session.execute(text("DELETE FROM passages WHERE id = :id"), {"id": str(p2.id)})
    await db_session.commit()

    # Resolve should only include p1
    scope_ids = await resolve_scope(db_session, scope)
    assert p1.id in scope_ids
    assert p2.id not in scope_ids


# =============================================================================
# Scoped Search
# =============================================================================


@pytest.mark.docker
async def test_search_in_scope_fts(db_session: AsyncSession, mock_embedding_fn: AsyncMock) -> None:
    """Test FTS search within a scope."""
    with patch("kp3.services.search.generate_embedding", mock_embedding_fn):
        scope = await create_scope(db_session, "search-fts", "test-agent")

        # Create passages - some in scope, some not
        in_scope = await create_passage(
            db_session,
            "Python programming tutorial",
            "tutorial",
            agent_id="test-agent",
            embedding_openai=[0.5] * 1024,
        )
        out_of_scope = await create_passage(
            db_session,
            "Python web framework guide",
            "tutorial",
            agent_id="test-agent",
            embedding_openai=[0.5] * 1024,
        )
        await add_passages_to_scope(db_session, scope, [in_scope.id])
        await db_session.commit()

        # Search within scope
        scope_ids = await resolve_scope(db_session, scope)
        results = await search_passages(
            db_session,
            "Python",
            mode="fts",
            agent_id="test-agent",
            scope_ids=scope_ids,
        )

        result_ids = [r.id for r in results]
        assert in_scope.id in result_ids
        assert out_of_scope.id not in result_ids


@pytest.mark.docker
async def test_search_in_scope_semantic(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test semantic search within a scope."""
    with patch("kp3.services.search.generate_embedding", mock_embedding_fn):
        scope = await create_scope(db_session, "search-semantic", "test-agent")

        in_scope = await create_passage(
            db_session,
            "Machine learning algorithms",
            "article",
            agent_id="test-agent",
            embedding_openai=[0.5] * 1024,
        )
        out_of_scope = await create_passage(
            db_session,
            "Deep learning neural networks",
            "article",
            agent_id="test-agent",
            embedding_openai=[0.5] * 1024,
        )
        await add_passages_to_scope(db_session, scope, [in_scope.id])
        await db_session.commit()

        scope_ids = await resolve_scope(db_session, scope)
        results = await search_passages(
            db_session,
            "AI",
            mode="semantic",
            agent_id="test-agent",
            scope_ids=scope_ids,
        )

        result_ids = [r.id for r in results]
        assert in_scope.id in result_ids
        assert out_of_scope.id not in result_ids


@pytest.mark.docker
async def test_search_in_scope_hybrid(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test hybrid search within a scope."""
    with patch("kp3.services.search.generate_embedding", mock_embedding_fn):
        scope = await create_scope(db_session, "search-hybrid", "test-agent")

        in_scope = await create_passage(
            db_session,
            "Database optimization techniques",
            "guide",
            agent_id="test-agent",
            embedding_openai=[0.5] * 1024,
        )
        out_of_scope = await create_passage(
            db_session,
            "SQL query performance tuning",
            "guide",
            agent_id="test-agent",
            embedding_openai=[0.5] * 1024,
        )
        await add_passages_to_scope(db_session, scope, [in_scope.id])
        await db_session.commit()

        scope_ids = await resolve_scope(db_session, scope)
        results = await search_passages(
            db_session,
            "database",
            mode="hybrid",
            agent_id="test-agent",
            scope_ids=scope_ids,
        )

        result_ids = [r.id for r in results]
        assert in_scope.id in result_ids
        assert out_of_scope.id not in result_ids


@pytest.mark.docker
async def test_search_excludes_out_of_scope(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test that search correctly excludes out-of-scope passages."""
    with patch("kp3.services.search.generate_embedding", mock_embedding_fn):
        scope = await create_scope(db_session, "exclude-test", "test-agent")

        # Create many passages, only add some to scope
        all_passages = []
        for i in range(10):
            p = await create_passage(
                db_session,
                f"Test content {i} with keyword",
                "test",
                agent_id="test-agent",
                embedding_openai=[0.5] * 1024,
            )
            all_passages.append(p)

        # Only first 3 in scope
        in_scope_ids = [p.id for p in all_passages[:3]]
        await add_passages_to_scope(db_session, scope, in_scope_ids)
        await db_session.commit()

        scope_ids = await resolve_scope(db_session, scope)
        results = await search_passages(
            db_session,
            "keyword",
            mode="fts",
            agent_id="test-agent",
            scope_ids=scope_ids,
        )

        result_ids = [r.id for r in results]
        assert len(result_ids) <= 3
        for rid in result_ids:
            assert rid in in_scope_ids


@pytest.mark.docker
async def test_search_empty_scope_returns_empty(
    db_session: AsyncSession, mock_embedding_fn: AsyncMock
) -> None:
    """Test that searching an empty scope returns no results."""
    with patch("kp3.services.search.generate_embedding", mock_embedding_fn):
        scope = await create_scope(db_session, "empty-search", "test-agent")
        await db_session.commit()

        scope_ids = await resolve_scope(db_session, scope)
        results = await search_passages(
            db_session,
            "anything",
            mode="fts",
            agent_id="test-agent",
            scope_ids=scope_ids,
        )

        assert results == []


# =============================================================================
# History & Revert
# =============================================================================


@pytest.mark.docker
async def test_scope_history_recorded(db_session: AsyncSession) -> None:
    """Test that scope changes are recorded in history."""
    scope = await create_scope(db_session, "history-test", "test-agent")
    await db_session.commit()

    # Make some changes
    p1 = await create_passage(db_session, "H1", "test", agent_id="test-agent")
    await add_passages_to_scope(db_session, scope, [p1.id])
    await add_refs_to_scope(db_session, scope, ["ref1"])
    await db_session.commit()

    history = await get_scope_history(db_session, scope)

    # Should have at least 3 entries: initial + 2 changes
    assert len(history) >= 3

    # Versions should be descending
    versions = [h["version"] for h in history]
    assert versions == sorted(versions, reverse=True)


@pytest.mark.docker
async def test_scope_history_order(db_session: AsyncSession) -> None:
    """Test that history is returned newest first."""
    scope = await create_scope(db_session, "history-order", "test-agent")
    await db_session.commit()

    # Make several changes
    for i in range(5):
        p = await create_passage(db_session, f"Change {i}", "test", agent_id="test-agent")
        await add_passages_to_scope(db_session, scope, [p.id])
    await db_session.commit()

    history = await get_scope_history(db_session, scope)

    # Check ordering by changed_at
    for i in range(len(history) - 1):
        assert history[i]["changed_at"] >= history[i + 1]["changed_at"]


@pytest.mark.docker
async def test_revert_scope_to_version(db_session: AsyncSession) -> None:
    """Test reverting a scope to a previous version."""
    scope = await create_scope(db_session, "revert-test", "test-agent")
    await db_session.commit()

    # Version 1: empty
    # Version 2: add p1
    p1 = await create_passage(db_session, "P1", "test", agent_id="test-agent")
    await add_passages_to_scope(db_session, scope, [p1.id])

    # Version 3: add p2
    p2 = await create_passage(db_session, "P2", "test", agent_id="test-agent")
    await add_passages_to_scope(db_session, scope, [p2.id])
    await db_session.commit()

    # Current version should be 3
    assert await get_current_version(db_session, scope) == 3

    # Revert to version 2
    new_version, reverted_from = await revert_scope(db_session, scope, to_version=2)
    await db_session.commit()

    assert reverted_from == 3
    assert new_version == 4  # Revert creates a new version

    # Resolve should show only p1 (state at version 2)
    scope_ids = await resolve_scope(db_session, scope)
    assert p1.id in scope_ids
    assert p2.id not in scope_ids


@pytest.mark.docker
async def test_revert_creates_new_history_entry(db_session: AsyncSession) -> None:
    """Test that reverting creates a new history entry (non-destructive)."""
    scope = await create_scope(db_session, "revert-history", "test-agent")
    await db_session.commit()

    p1 = await create_passage(db_session, "P1", "test", agent_id="test-agent")
    await add_passages_to_scope(db_session, scope, [p1.id])
    await db_session.commit()

    history_before = await get_scope_history(db_session, scope)

    # Revert to version 1
    await revert_scope(db_session, scope, to_version=1)
    await db_session.commit()

    history_after = await get_scope_history(db_session, scope)

    # Should have one more entry
    assert len(history_after) == len(history_before) + 1


@pytest.mark.docker
async def test_revert_invalid_version_fails(db_session: AsyncSession) -> None:
    """Test that reverting to an invalid version raises an error."""
    scope = await create_scope(db_session, "revert-invalid", "test-agent")
    await db_session.commit()

    # Can't revert to current version
    with pytest.raises(ValueError, match="Cannot revert"):
        await revert_scope(db_session, scope, to_version=1)

    # Can't revert to future version
    with pytest.raises(ValueError, match="Cannot revert"):
        await revert_scope(db_session, scope, to_version=999)


# =============================================================================
# API Endpoint Tests
# =============================================================================


@pytest.mark.docker
async def test_api_create_scope(test_client: AsyncClient) -> None:
    """Test POST /scopes endpoint."""
    response = await test_client.post(
        "/scopes",
        json={"name": "api-scope", "description": "Created via API"},
        headers={"X-Agent-ID": "test-agent"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "api-scope"
    assert data["description"] == "Created via API"
    assert data["agent_id"] == "test-agent"
    assert "id" in data
    assert "head_ref" in data


@pytest.mark.docker
async def test_api_create_duplicate_scope_fails(test_client: AsyncClient) -> None:
    """Test that creating a duplicate scope returns 409."""
    await test_client.post(
        "/scopes",
        json={"name": "unique-api-scope"},
        headers={"X-Agent-ID": "test-agent"},
    )

    response = await test_client.post(
        "/scopes",
        json={"name": "unique-api-scope"},
        headers={"X-Agent-ID": "test-agent"},
    )

    assert response.status_code == 409


@pytest.mark.docker
async def test_api_list_scopes(test_client: AsyncClient) -> None:
    """Test GET /scopes endpoint."""
    # Create some scopes
    for name in ["list-a", "list-b", "list-c"]:
        await test_client.post(
            "/scopes",
            json={"name": name},
            headers={"X-Agent-ID": "test-agent"},
        )

    response = await test_client.get(
        "/scopes",
        headers={"X-Agent-ID": "test-agent"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "scopes" in data
    assert data["count"] >= 3


@pytest.mark.docker
async def test_api_get_scope(test_client: AsyncClient) -> None:
    """Test GET /scopes/{name} endpoint."""
    await test_client.post(
        "/scopes",
        json={"name": "get-test"},
        headers={"X-Agent-ID": "test-agent"},
    )

    response = await test_client.get(
        "/scopes/get-test",
        headers={"X-Agent-ID": "test-agent"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "get-test"


@pytest.mark.docker
async def test_api_get_nonexistent_scope(test_client: AsyncClient) -> None:
    """Test GET /scopes/{name} for non-existent scope."""
    response = await test_client.get(
        "/scopes/nonexistent-api",
        headers={"X-Agent-ID": "test-agent"},
    )

    assert response.status_code == 404


@pytest.mark.docker
async def test_api_delete_scope(test_client: AsyncClient) -> None:
    """Test DELETE /scopes/{name} endpoint."""
    await test_client.post(
        "/scopes",
        json={"name": "deletable-api"},
        headers={"X-Agent-ID": "test-agent"},
    )

    response = await test_client.delete(
        "/scopes/deletable-api",
        headers={"X-Agent-ID": "test-agent"},
    )
    assert response.status_code == 204

    # Verify it's gone
    get_response = await test_client.get(
        "/scopes/deletable-api",
        headers={"X-Agent-ID": "test-agent"},
    )
    assert get_response.status_code == 404


@pytest.mark.docker
async def test_api_create_passage_in_scope(
    test_client: AsyncClient, mock_embedding_fn: AsyncMock
) -> None:
    """Test POST /scopes/{name}/passages endpoint."""
    with patch("kp3.query_service.router.generate_embedding", mock_embedding_fn):
        # Create scope
        await test_client.post(
            "/scopes",
            json={"name": "passage-api"},
            headers={"X-Agent-ID": "test-agent"},
        )

        # Create passage in scope
        response = await test_client.post(
            "/scopes/passage-api/passages",
            json={"content": "API passage content", "passage_type": "memory"},
            headers={"X-Agent-ID": "test-agent"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "API passage content"
        assert data["passage_type"] == "memory"
        assert data["scope_version"] == 2


@pytest.mark.docker
async def test_api_add_to_scope(test_client: AsyncClient, mock_embedding_fn: AsyncMock) -> None:
    """Test POST /scopes/{name}/add endpoint."""
    with patch("kp3.query_service.router.generate_embedding", mock_embedding_fn):
        # Create scope
        await test_client.post(
            "/scopes",
            json={"name": "add-api"},
            headers={"X-Agent-ID": "test-agent"},
        )

        # Create a passage
        passage_response = await test_client.post(
            "/passages",
            json={"content": "External passage", "passage_type": "test"},
            headers={"X-Agent-ID": "test-agent"},
        )
        passage_id = passage_response.json()["id"]

        # Add to scope
        response = await test_client.post(
            "/scopes/add-api/add",
            json={"passage_ids": [passage_id], "refs": ["some/ref"]},
            headers={"X-Agent-ID": "test-agent"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["modified_count"] == 2  # 1 passage + 1 ref


@pytest.mark.docker
async def test_api_remove_from_scope(
    test_client: AsyncClient, mock_embedding_fn: AsyncMock
) -> None:
    """Test POST /scopes/{name}/remove endpoint."""
    with patch("kp3.query_service.router.generate_embedding", mock_embedding_fn):
        # Create scope and add content
        await test_client.post(
            "/scopes",
            json={"name": "remove-api"},
            headers={"X-Agent-ID": "test-agent"},
        )

        await test_client.post(
            "/scopes/remove-api/add",
            json={"refs": ["ref1", "ref2"]},
            headers={"X-Agent-ID": "test-agent"},
        )

        # Remove
        response = await test_client.post(
            "/scopes/remove-api/remove",
            json={"refs": ["ref1"]},
            headers={"X-Agent-ID": "test-agent"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["modified_count"] == 1


@pytest.mark.docker
async def test_api_scope_history(test_client: AsyncClient, mock_embedding_fn: AsyncMock) -> None:
    """Test GET /scopes/{name}/history endpoint."""
    with patch("kp3.query_service.router.generate_embedding", mock_embedding_fn):
        await test_client.post(
            "/scopes",
            json={"name": "history-api"},
            headers={"X-Agent-ID": "test-agent"},
        )

        # Make some changes
        await test_client.post(
            "/scopes/history-api/add",
            json={"refs": ["ref1"]},
            headers={"X-Agent-ID": "test-agent"},
        )

        response = await test_client.get(
            "/scopes/history-api/history",
            headers={"X-Agent-ID": "test-agent"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert data["count"] >= 2


@pytest.mark.docker
async def test_api_revert_scope(test_client: AsyncClient, mock_embedding_fn: AsyncMock) -> None:
    """Test POST /scopes/{name}/revert endpoint."""
    with patch("kp3.query_service.router.generate_embedding", mock_embedding_fn):
        await test_client.post(
            "/scopes",
            json={"name": "revert-api"},
            headers={"X-Agent-ID": "test-agent"},
        )

        await test_client.post(
            "/scopes/revert-api/add",
            json={"refs": ["ref1"]},
            headers={"X-Agent-ID": "test-agent"},
        )

        response = await test_client.post(
            "/scopes/revert-api/revert",
            json={"to_version": 1},
            headers={"X-Agent-ID": "test-agent"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["scope_version"] == 3  # revert creates new version
        assert data["reverted_from"] == 2


@pytest.mark.docker
async def test_api_search_in_scope(test_client: AsyncClient, mock_embedding_fn: AsyncMock) -> None:
    """Test GET /scopes/{name}/search endpoint."""
    with patch("kp3.query_service.router.generate_embedding", mock_embedding_fn):
        with patch("kp3.services.search.generate_embedding", mock_embedding_fn):
            # Create scope
            await test_client.post(
                "/scopes",
                json={"name": "search-api"},
                headers={"X-Agent-ID": "test-agent"},
            )

            # Create passage in scope
            await test_client.post(
                "/scopes/search-api/passages",
                json={"content": "Searchable Python content", "passage_type": "memory"},
                headers={"X-Agent-ID": "test-agent"},
            )

            # Search within scope
            response = await test_client.get(
                "/scopes/search-api/search",
                params={"query": "Python", "mode": "fts"},
                headers={"X-Agent-ID": "test-agent"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["scope"] == "search-api"
            assert "scope_version" in data
            assert data["count"] >= 1


@pytest.mark.docker
async def test_api_search_empty_scope(
    test_client: AsyncClient, mock_embedding_fn: AsyncMock
) -> None:
    """Test searching an empty scope via API."""
    with patch("kp3.services.search.generate_embedding", mock_embedding_fn):
        await test_client.post(
            "/scopes",
            json={"name": "empty-search-api"},
            headers={"X-Agent-ID": "test-agent"},
        )

        response = await test_client.get(
            "/scopes/empty-search-api/search",
            params={"query": "anything"},
            headers={"X-Agent-ID": "test-agent"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["results"] == []


# =============================================================================
# Edge Cases
# =============================================================================


@pytest.mark.docker
async def test_create_passage_in_nonexistent_scope(test_client: AsyncClient) -> None:
    """Test creating a passage in a non-existent scope returns 404."""
    response = await test_client.post(
        "/scopes/nonexistent/passages",
        json={"content": "Test", "passage_type": "test"},
        headers={"X-Agent-ID": "test-agent"},
    )
    assert response.status_code == 404


@pytest.mark.docker
async def test_add_to_nonexistent_scope(test_client: AsyncClient) -> None:
    """Test adding to a non-existent scope returns 404."""
    response = await test_client.post(
        "/scopes/nonexistent/add",
        json={"refs": ["ref1"]},
        headers={"X-Agent-ID": "test-agent"},
    )
    assert response.status_code == 404


@pytest.mark.docker
async def test_revert_to_invalid_version_via_api(test_client: AsyncClient) -> None:
    """Test reverting to invalid version via API returns 400."""
    await test_client.post(
        "/scopes",
        json={"name": "revert-invalid-api"},
        headers={"X-Agent-ID": "test-agent"},
    )

    response = await test_client.post(
        "/scopes/revert-invalid-api/revert",
        json={"to_version": 1},  # Can't revert to current
        headers={"X-Agent-ID": "test-agent"},
    )

    assert response.status_code == 400
