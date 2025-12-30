"""Tests for step_memory_blocks job."""

from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kairix_agent.events.models import EventType
from kairix_agent.worker.jobs.step_memory import (
    STEP_MEMORY_JOB,
    StepResult,
    _fetch_blocks,
    _parse_step_response,
    _run_step_agent,
    step_memory_blocks,
)


class TestStepResult:
    """Tests for StepResult dataclass."""

    def test_step_result_with_update(self) -> None:
        """StepResult correctly stores update information."""
        result = StepResult(
            block_label="persona",
            updated=True,
            new_value="Updated persona text",
            rationale="Identity shift detected",
            passage_id="passage-123",
            searched_kp3=True,
        )
        assert result.block_label == "persona"
        assert result.updated is True
        assert result.new_value == "Updated persona text"
        assert result.rationale == "Identity shift detected"
        assert result.passage_id == "passage-123"
        assert result.searched_kp3 is True
        assert result.error is None

    def test_step_result_no_update(self) -> None:
        """StepResult correctly stores no-update information."""
        result = StepResult(
            block_label="human",
            updated=False,
            new_value=None,
            rationale="No significant changes observed",
            passage_id=None,
            searched_kp3=False,
        )
        assert result.block_label == "human"
        assert result.updated is False
        assert result.new_value is None
        assert result.rationale == "No significant changes observed"
        assert result.searched_kp3 is False

    def test_step_result_with_error(self) -> None:
        """StepResult correctly stores error information."""
        result = StepResult(
            block_label="world",
            updated=False,
            new_value=None,
            rationale=None,
            passage_id=None,
            searched_kp3=False,
            error="Connection timeout",
        )
        assert result.error == "Connection timeout"
        assert result.updated is False
        assert result.rationale is None


class TestParseStepResponse:
    """Tests for _parse_step_response function."""

    def test_parse_updating_with_rationale(self) -> None:
        """Parses UPDATING: format with rationale and new value."""
        response = """UPDATING: The user mentioned a new project that seems significant.

This is the new block content that should be stored."""

        updated, rationale, new_value = _parse_step_response(response)

        assert updated is True
        assert rationale == "The user mentioned a new project that seems significant."
        assert new_value == "This is the new block content that should be stored."

    def test_parse_updating_without_clear_separation(self) -> None:
        """Parses UPDATING: format without double newline separation."""
        response = "UPDATING: New content here"

        updated, rationale, new_value = _parse_step_response(response)

        assert updated is True
        assert rationale == "Update triggered"
        assert new_value == "New content here"

    def test_parse_no_update_needed_with_rationale(self) -> None:
        """Parses NO_UPDATE_NEEDED: format with rationale."""
        response = "NO_UPDATE_NEEDED: The session summary contained only routine interactions."

        updated, rationale, new_value = _parse_step_response(response)

        assert updated is False
        assert rationale == "The session summary contained only routine interactions."
        assert new_value is None

    def test_parse_legacy_no_update_format(self) -> None:
        """Parses legacy NO_UPDATE_NEEDED format (without colon)."""
        response = "NO_UPDATE_NEEDED"

        updated, rationale, new_value = _parse_step_response(response)

        assert updated is False
        assert rationale == "No rationale provided"
        assert new_value is None

    def test_parse_legacy_update_format(self) -> None:
        """Parses legacy format without prefix (treated as update)."""
        response = "This is the new block content directly without prefix."

        updated, rationale, new_value = _parse_step_response(response)

        assert updated is True
        assert rationale == "Update triggered (legacy format)"
        assert new_value == "This is the new block content directly without prefix."

    def test_parse_case_insensitive(self) -> None:
        """Response parsing is case-insensitive for prefixes."""
        response = "no_update_needed: Nothing changed"

        updated, rationale, _new_value = _parse_step_response(response)

        assert updated is False
        assert rationale == "Nothing changed"

    def test_parse_strips_whitespace(self) -> None:
        """Response parsing strips whitespace from components."""
        response = "  UPDATING:  Some rationale here  \n\n  New content  "

        updated, rationale, new_value = _parse_step_response(response)

        assert updated is True
        assert rationale == "Some rationale here"
        assert new_value == "New content"


class TestFetchBlocks:
    """Tests for _fetch_blocks helper function."""

    @pytest.mark.asyncio
    async def test_fetches_all_blocks(self) -> None:
        """Fetches and returns all blocks from Letta."""
        # Create mock blocks
        mock_blocks = [
            MagicMock(label="persona", value="I am an AI assistant"),
            MagicMock(label="human", value="The user is a developer"),
            MagicMock(label="world", value="Projects: Kairix"),
        ]

        # Create async iterator mock
        async def mock_list(
            *args: object, **kwargs: object
        ) -> AsyncIterator[MagicMock]:
            for block in mock_blocks:
                yield block

        mock_client = AsyncMock()
        mock_client.agents.blocks.list = mock_list

        result = await _fetch_blocks(mock_client, "agent-123")

        assert len(result) == 3
        assert result["persona"] == "I am an AI assistant"
        assert result["human"] == "The user is a developer"
        assert result["world"] == "Projects: Kairix"

    @pytest.mark.asyncio
    async def test_handles_empty_values(self) -> None:
        """Handles blocks with None/empty values."""
        mock_blocks = [
            MagicMock(label="persona", value=None),
            MagicMock(label="human", value=""),
        ]

        async def mock_list(
            *args: object, **kwargs: object
        ) -> AsyncIterator[MagicMock]:
            for block in mock_blocks:
                yield block

        mock_client = AsyncMock()
        mock_client.agents.blocks.list = mock_list

        result = await _fetch_blocks(mock_client, "agent-123")

        assert result["persona"] == ""
        assert result["human"] == ""


class TestRunStepAgent:
    """Tests for _run_step_agent helper function."""

    @pytest.mark.asyncio
    async def test_returns_no_update_needed(self) -> None:
        """Returns StepResult with updated=False when agent returns NO_UPDATE_NEEDED."""
        mock_config = MagicMock()
        mock_config.target_block = "persona"

        mock_client = AsyncMock()

        with patch(
            "kairix_agent.worker.jobs.step_memory.BlockManagerAgent"
        ) as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(return_value="NO_UPDATE_NEEDED")
            mock_agent.register_tool_handler = MagicMock()
            mock_agent_class.return_value = mock_agent

            result = await _run_step_agent(
                config=mock_config,
                agent_id="agent-123",
                client=mock_client,
                blocks={"persona": "current", "human": "human", "world": "world"},
                session_summary="Test summary",
                metadata={"period_start": "2024-01-01"},
            )

            assert result.block_label == "persona"
            assert result.updated is False
            assert result.new_value is None

    @pytest.mark.asyncio
    async def test_returns_updated_block(self) -> None:
        """Returns StepResult with updated=True when agent returns new content."""
        mock_config = MagicMock()
        mock_config.target_block = "human"

        mock_client = AsyncMock()

        with patch(
            "kairix_agent.worker.jobs.step_memory.BlockManagerAgent"
        ) as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(return_value="Updated human block content")
            mock_agent.register_tool_handler = MagicMock()
            mock_agent_class.return_value = mock_agent

            result = await _run_step_agent(
                config=mock_config,
                agent_id="agent-123",
                client=mock_client,
                blocks={"persona": "p", "human": "h", "world": "w"},
                session_summary="Test summary",
                metadata={},
            )

            assert result.block_label == "human"
            assert result.updated is True
            assert result.new_value == "Updated human block content"

    @pytest.mark.asyncio
    async def test_tracks_search_kp3_usage(self) -> None:
        """Tracks when search_kp3 tool is used."""
        mock_config = MagicMock()
        mock_config.target_block = "world"

        mock_client = AsyncMock()

        with (
            patch(
                "kairix_agent.worker.jobs.step_memory.BlockManagerAgent"
            ) as mock_agent_class,
            patch(
                "kairix_agent.worker.jobs.step_memory.handle_search_kp3"
            ) as mock_search,
        ):
            mock_search.return_value = "Search results"

            # Capture the registered tool handler
            # Type: async callable that takes (query, limit) and returns str
            registered_handler: Callable[..., Coroutine[Any, Any, str]] | None = None

            def capture_handler(
                name: str, handler: Callable[..., Coroutine[Any, Any, str]]
            ) -> None:
                nonlocal registered_handler
                if name == "search_kp3":
                    registered_handler = handler

            mock_agent = AsyncMock()

            async def run_with_search(*args: object, **kwargs: object) -> str:
                # Simulate the agent calling the search tool
                if registered_handler:
                    await registered_handler("test query")
                return "Updated world"

            mock_agent.run = run_with_search
            mock_agent.register_tool_handler = capture_handler
            mock_agent_class.return_value = mock_agent

            result = await _run_step_agent(
                config=mock_config,
                agent_id="agent-123",
                client=mock_client,
                blocks={"persona": "p", "human": "h", "world": "w"},
                session_summary="Test summary",
                metadata={},
            )

            assert result.searched_kp3 is True

    @pytest.mark.asyncio
    async def test_handles_agent_error(self) -> None:
        """Returns StepResult with error when agent raises exception."""
        mock_config = MagicMock()
        mock_config.target_block = "persona"

        mock_client = AsyncMock()

        with patch(
            "kairix_agent.worker.jobs.step_memory.BlockManagerAgent"
        ) as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(side_effect=TimeoutError("LLM timeout"))
            mock_agent.register_tool_handler = MagicMock()
            mock_agent_class.return_value = mock_agent

            result = await _run_step_agent(
                config=mock_config,
                agent_id="agent-123",
                client=mock_client,
                blocks={},
                session_summary="Test",
                metadata={},
            )

            assert result.block_label == "persona"
            assert result.updated is False
            assert result.error is not None
            assert "timeout" in result.error.lower()


class TestStepMemoryBlocks:
    """Tests for step_memory_blocks main job function."""

    @pytest.mark.asyncio
    async def test_job_name_constant(self) -> None:
        """Job name constant is set correctly."""
        assert STEP_MEMORY_JOB == "step_memory_blocks"

    @pytest.mark.asyncio
    async def test_runs_three_step_agents_in_parallel(self) -> None:
        """Runs persona, human, and world step agents in parallel."""
        mock_ctx: dict[str, object] = {}

        with (
            patch(
                "kairix_agent.worker.jobs.step_memory.AsyncLetta"
            ) as mock_letta_class,
            patch(
                "kairix_agent.worker.jobs.step_memory._fetch_blocks"
            ) as mock_fetch,
            patch(
                "kairix_agent.worker.jobs.step_memory._run_step_agent"
            ) as mock_run,
            patch("kairix_agent.worker.jobs.step_memory.publish_event"),
            patch(
                "kairix_agent.worker.jobs.step_memory.emit_context_state"
            ) as mock_emit,
        ):
            mock_letta_class.return_value = AsyncMock()
            mock_fetch.return_value = {
                "persona": "p",
                "human": "h",
                "world": "w",
            }

            # All three agents return NO_UPDATE_NEEDED
            mock_run.return_value = StepResult(
                block_label="test",
                updated=False,
                new_value=None,
                rationale="No changes needed",
                passage_id=None,
                searched_kp3=False,
            )

            result = await step_memory_blocks(
                mock_ctx,  # type: ignore[arg-type]
                agent_id="agent-123",
                letta_url="http://localhost:8283",
                session_summary="Test summary",
                period_start="2024-01-01T00:00:00Z",
                period_end="2024-01-01T01:00:00Z",
            )

            # Should run 3 step agents
            assert mock_run.call_count == 3

            # Should emit context state at the end
            mock_emit.assert_called_once_with(
                agent_id="agent-123", letta_url="http://localhost:8283"
            )

            assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_publishes_events_for_each_block(self) -> None:
        """Publishes step complete events for each block."""
        mock_ctx: dict[str, object] = {}

        with (
            patch(
                "kairix_agent.worker.jobs.step_memory.AsyncLetta"
            ) as mock_letta_class,
            patch(
                "kairix_agent.worker.jobs.step_memory._fetch_blocks"
            ) as mock_fetch,
            patch(
                "kairix_agent.worker.jobs.step_memory._run_step_agent"
            ) as mock_run,
            patch(
                "kairix_agent.worker.jobs.step_memory.publish_event"
            ) as mock_publish,
            patch("kairix_agent.worker.jobs.step_memory.emit_context_state"),
        ):
            mock_letta_class.return_value = AsyncMock()
            mock_fetch.return_value = {"persona": "", "human": "", "world": ""}

            # Each agent returns different results
            mock_run.side_effect = [
                StepResult(
                    block_label="persona",
                    updated=True,
                    new_value="New persona",
                    rationale="Relationship deepened",
                    passage_id=None,
                    searched_kp3=False,
                ),
                StepResult(
                    block_label="human",
                    updated=False,
                    new_value=None,
                    rationale="No identity changes",
                    passage_id=None,
                    searched_kp3=True,
                ),
                StepResult(
                    block_label="world",
                    updated=True,
                    new_value="New world",
                    rationale="New project mentioned",
                    passage_id=None,
                    searched_kp3=True,
                ),
            ]

            result = await step_memory_blocks(
                mock_ctx,  # type: ignore[arg-type]
                agent_id="agent-123",
                letta_url="http://localhost:8283",
                session_summary="Test",
                period_start="2024-01-01T00:00:00Z",
                period_end="2024-01-01T01:00:00Z",
            )

            # Should publish 3 events
            assert mock_publish.call_count == 3

            # Check event types were correct
            event_types = [call[1]["event_type"] for call in mock_publish.call_args_list]
            assert EventType.PERSONA_STEP_COMPLETE in event_types
            assert EventType.HUMAN_STEP_COMPLETE in event_types
            assert EventType.WORLD_STEP_COMPLETE in event_types

            # Check blocks output
            assert result["status"] == "ok"
            blocks_result = result["blocks"]
            assert blocks_result["persona"]["updated"] is True  # type: ignore[index]
            assert blocks_result["human"]["updated"] is False  # type: ignore[index]
            assert blocks_result["world"]["searched_kp3"] is True  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_handles_agent_exception(self) -> None:
        """Continues processing when one agent raises an exception."""
        mock_ctx: dict[str, object] = {}

        with (
            patch(
                "kairix_agent.worker.jobs.step_memory.AsyncLetta"
            ) as mock_letta_class,
            patch(
                "kairix_agent.worker.jobs.step_memory._fetch_blocks"
            ) as mock_fetch,
            patch(
                "kairix_agent.worker.jobs.step_memory._run_step_agent"
            ) as mock_run,
            patch(
                "kairix_agent.worker.jobs.step_memory.publish_event"
            ) as mock_publish,
            patch("kairix_agent.worker.jobs.step_memory.emit_context_state"),
        ):
            mock_letta_class.return_value = AsyncMock()
            mock_fetch.return_value = {"persona": "", "human": "", "world": ""}

            # First agent raises exception, others succeed
            mock_run.side_effect = [
                RuntimeError("Agent failed"),
                StepResult(
                    block_label="human",
                    updated=False,
                    new_value=None,
                    rationale="No changes",
                    passage_id=None,
                    searched_kp3=False,
                ),
                StepResult(
                    block_label="world",
                    updated=True,
                    new_value="Updated",
                    rationale="New element added",
                    passage_id=None,
                    searched_kp3=False,
                ),
            ]

            result = await step_memory_blocks(
                mock_ctx,  # type: ignore[arg-type]
                agent_id="agent-123",
                letta_url="http://localhost:8283",
                session_summary="Test",
                period_start="2024-01-01T00:00:00Z",
                period_end="2024-01-01T01:00:00Z",
            )

            # Should still succeed overall
            assert result["status"] == "ok"

            # Should only publish 2 events (skipping failed agent)
            assert mock_publish.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_error_on_complete_failure(self) -> None:
        """Returns error status when entire job fails."""
        mock_ctx: dict[str, object] = {}

        with patch(
            "kairix_agent.worker.jobs.step_memory.AsyncLetta"
        ) as mock_letta_class:
            mock_letta_class.side_effect = ConnectionError("Cannot connect to Letta")

            result = await step_memory_blocks(
                mock_ctx,  # type: ignore[arg-type]
                agent_id="agent-123",
                letta_url="http://localhost:8283",
                session_summary="Test",
                period_start="2024-01-01T00:00:00Z",
                period_end="2024-01-01T01:00:00Z",
            )

            assert result["status"] == "error"
            assert "Cannot connect" in str(result["error"])
