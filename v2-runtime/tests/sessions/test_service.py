"""Tests for session tracking service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from kairix_agent.sessions.models import Session, SessionMessage, SessionStatus


class TestSessionModels:
    """Tests for session models."""

    def test_session_status_enum_values(self) -> None:
        """SessionStatus enum has expected values."""
        assert SessionStatus.PENDING.value == "pending"
        assert SessionStatus.SUMMARIZED.value == "summarized"
        assert SessionStatus.FAILED.value == "failed"

    def test_session_model_nullable_fields(self) -> None:
        """Session model allows null for optional fields."""
        session = Session(
            agent_id="agent-123",
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
            message_count=5,
            status=SessionStatus.PENDING.value,
        )
        assert session.agent_id == "agent-123"
        assert session.message_count == 5
        # Optional fields can be None
        assert session.summary_passage_id is None
        assert session.error_message is None
        assert session.summarized_at is None

    def test_session_message_model(self) -> None:
        """SessionMessage model works correctly."""
        session_id = str(uuid4())
        msg = SessionMessage(session_id=session_id, message_id="msg-abc-123")
        assert msg.session_id == session_id
        assert msg.message_id == "msg-abc-123"


class TestGetLatestSessionEnd:
    """Tests for get_latest_session_end function."""

    @pytest.mark.asyncio
    async def test_no_sessions_returns_none(self) -> None:
        """Returns None when no sessions exist for the agent."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "kairix_agent.sessions.service._async_session",
            return_value=mock_session_factory,
        ):
            from kairix_agent.sessions.service import get_latest_session_end

            result = await get_latest_session_end("agent-123")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_latest_session_end(self) -> None:
        """Returns period_end of the most recent session."""
        expected_time = datetime.now(UTC)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_time
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "kairix_agent.sessions.service._async_session",
            return_value=mock_session_factory,
        ):
            from kairix_agent.sessions.service import get_latest_session_end

            result = await get_latest_session_end("agent-123")
            assert result == expected_time


class TestCreateSession:
    """Tests for create_session function."""

    @pytest.mark.asyncio
    async def test_creates_session_with_messages(self) -> None:
        """Creates a session and associates message IDs."""
        # Mock the database session
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Create mock async context manager
        mock_session_factory = MagicMock()
        mock_session_factory.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "kairix_agent.sessions.service._async_session",
            return_value=mock_session_factory,
        ):
            from kairix_agent.sessions.service import create_session

            now = datetime.now(UTC)
            result = await create_session(
                agent_id="agent-123",
                message_ids=["msg-1", "msg-2", "msg-3"],
                period_start=now - timedelta(hours=1),
                period_end=now,
            )

            # Verify session was created with correct attributes
            assert result.agent_id == "agent-123"
            assert result.message_count == 3
            assert result.status == SessionStatus.PENDING.value

            # Verify add was called (session + 3 messages = 4 calls)
            assert mock_db.add.call_count == 4
            mock_db.flush.assert_called_once()
            mock_db.commit.assert_called_once()


class TestUpdateSessionStatus:
    """Tests for update_session_status function."""

    @pytest.mark.asyncio
    async def test_updates_to_summarized(self) -> None:
        """Updates session status to summarized with passage ID."""
        mock_session = Session(
            id=str(uuid4()),
            agent_id="agent-123",
            period_start=datetime.now(UTC) - timedelta(hours=1),
            period_end=datetime.now(UTC),
            message_count=5,
            status=SessionStatus.PENDING.value,
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        mock_session_factory = MagicMock()
        mock_session_factory.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "kairix_agent.sessions.service._async_session",
            return_value=mock_session_factory,
        ):
            from kairix_agent.sessions.service import update_session_status

            now = datetime.now(UTC)
            result = await update_session_status(
                session_id=mock_session.id,
                status=SessionStatus.SUMMARIZED,
                summary_passage_id="passage-abc",
                summarized_at=now,
            )

            assert result is not None
            assert result.status == SessionStatus.SUMMARIZED.value
            assert result.summary_passage_id == "passage-abc"
            assert result.summarized_at == now

    @pytest.mark.asyncio
    async def test_updates_to_failed(self) -> None:
        """Updates session status to failed with error message."""
        mock_session = Session(
            id=str(uuid4()),
            agent_id="agent-123",
            period_start=datetime.now(UTC) - timedelta(hours=1),
            period_end=datetime.now(UTC),
            message_count=5,
            status=SessionStatus.PENDING.value,
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        mock_session_factory = MagicMock()
        mock_session_factory.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "kairix_agent.sessions.service._async_session",
            return_value=mock_session_factory,
        ):
            from kairix_agent.sessions.service import update_session_status

            result = await update_session_status(
                session_id=mock_session.id,
                status=SessionStatus.FAILED,
                error_message="Something went wrong",
            )

            assert result is not None
            assert result.status == SessionStatus.FAILED.value
            assert result.error_message == "Something went wrong"

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_session(self) -> None:
        """Returns None if session not found."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "kairix_agent.sessions.service._async_session",
            return_value=mock_session_factory,
        ):
            from kairix_agent.sessions.service import update_session_status

            result = await update_session_status(
                session_id="nonexistent-session",
                status=SessionStatus.FAILED,
            )

            assert result is None
