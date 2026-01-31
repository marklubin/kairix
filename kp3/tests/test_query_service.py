"""E2E tests for the KP3 query service."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import Passage
from kp3.services.search import search_passages


@pytest.mark.docker
class TestSearchService:
    """Tests for the search service."""

    @pytest.mark.asyncio
    async def test_fts_search_finds_matching_content(
        self, db_session: AsyncSession, sample_passages: list[Passage]
    ) -> None:
        """Test that FTS search returns passages matching the query."""
        results = await search_passages(
            db_session, "programming language", mode="fts", limit=5, agent_id="test-agent"
        )

        assert len(results) >= 1
        # Python passage should be found
        contents = [r.content for r in results]
        assert any("Python" in c for c in contents)

    @pytest.mark.asyncio
    async def test_fts_search_no_results(
        self, db_session: AsyncSession, sample_passages: list[Passage]
    ) -> None:
        """Test that FTS search returns empty list for non-matching query."""
        results = await search_passages(
            db_session, "xyznonexistent123", mode="fts", limit=5, agent_id="test-agent"
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fts_search_respects_limit(
        self, db_session: AsyncSession, sample_passages: list[Passage]
    ) -> None:
        """Test that FTS search respects the limit parameter."""
        # Search for a common term that should match multiple passages
        results = await search_passages(
            db_session, "Python", mode="fts", limit=1, agent_id="test-agent"
        )

        assert len(results) <= 1

    @pytest.mark.asyncio
    async def test_search_result_has_expected_fields(
        self, db_session: AsyncSession, sample_passages: list[Passage]
    ) -> None:
        """Test that search results have all expected fields."""
        results = await search_passages(
            db_session, "PostgreSQL", mode="fts", limit=1, agent_id="test-agent"
        )

        assert len(results) == 1
        result = results[0]
        assert result.id is not None
        assert result.content is not None
        assert result.passage_type is not None
        assert result.score is not None
        assert result.score > 0


@pytest.mark.docker
class TestRESTAPI:
    """Tests for the REST API endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, test_client: AsyncClient) -> None:
        """Test health check endpoint returns 200."""
        response = await test_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="Flaky when run after e2e tests due to connection pool/engine patching issues",
        strict=False,
    )
    async def test_search_endpoint_returns_results(
        self, test_client: AsyncClient, sample_passages: list[Passage]
    ) -> None:
        """Test that search endpoint returns matching passages."""
        response = await test_client.get(
            "/passages/search", params={"query": "Python", "mode": "fts", "limit": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "mode" in data
        assert "results" in data
        assert "count" in data
        assert data["query"] == "Python"
        assert data["mode"] == "fts"

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="Flaky due to event loop conflict between sample_passages and test_client fixtures",
        strict=False,
    )
    async def test_search_endpoint_with_results(
        self, test_client: AsyncClient, sample_passages: list[Passage]
    ) -> None:
        """Test that search endpoint finds expected passages."""
        response = await test_client.get(
            "/passages/search", params={"query": "programming language", "mode": "fts"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        assert len(data["results"]) >= 1

        # Check result structure
        result = data["results"][0]
        assert "id" in result
        assert "content" in result
        assert "passage_type" in result
        assert "score" in result

    @pytest.mark.asyncio
    @pytest.mark.vllm
    async def test_search_endpoint_default_mode(
        self, test_client: AsyncClient, sample_passages: list[Passage]
    ) -> None:
        """Test that search endpoint defaults to hybrid mode (requires vLLM/GPU)."""
        response = await test_client.get(
            "/passages/search", params={"query": "database"}
        )

        assert response.status_code == 200
        data = response.json()
        # Should default to hybrid mode (but without embeddings, only FTS matches)
        assert data["mode"] == "hybrid"

    @pytest.mark.asyncio
    async def test_search_endpoint_validates_limit(
        self, test_client: AsyncClient, sample_passages: list[Passage]
    ) -> None:
        """Test that search endpoint validates limit parameter."""
        # Limit too high
        response = await test_client.get(
            "/passages/search", params={"query": "test", "limit": 100}
        )
        assert response.status_code == 422  # Validation error

        # Limit too low
        response = await test_client.get(
            "/passages/search", params={"query": "test", "limit": 0}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_endpoint_requires_query(
        self, test_client: AsyncClient
    ) -> None:
        """Test that search endpoint requires query parameter."""
        response = await test_client.get("/passages/search")

        assert response.status_code == 422  # Missing required parameter
