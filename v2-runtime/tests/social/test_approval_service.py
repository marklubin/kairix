"""Tests for social approval queue service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from kairix_agent.social.models import ActionType, ApprovalStatus


class TestCreateApprovalItem:
    """Tests for create_approval_item function."""

    @pytest.mark.asyncio
    async def test_create_approval_item_basic(self) -> None:
        """Should create an approval item with required fields."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"
        channel_type = "bluesky"

        # Mock the database session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch(
            "kairix_agent.social.approval_service._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.social import approval_service

            item = await approval_service.create_approval_item(
                agent_id=agent_id,
                channel_type=channel_type,
                action_type=ActionType.REPLY,
            )

            # Verify session.add was called
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

            # The item should have been passed to add
            added_item = mock_session.add.call_args[0][0]
            assert added_item.agent_id == agent_id
            assert added_item.channel_type == channel_type
            assert added_item.action_type == ActionType.REPLY.value

    @pytest.mark.asyncio
    async def test_create_approval_item_with_all_fields(self) -> None:
        """Should create an approval item with all optional fields."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"
        interaction_id = str(uuid4())
        draft_content = "This is a draft reply"
        target_entity = "@researcher.bsky.social"
        context_summary = "Replying to interesting thread about AI"
        confidence_score = 0.85
        entity_model_used = "Entity model for @researcher..."

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch(
            "kairix_agent.social.approval_service._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.social import approval_service

            await approval_service.create_approval_item(
                agent_id=agent_id,
                channel_type="bluesky",
                action_type=ActionType.REPLY,
                interaction_id=interaction_id,
                draft_content=draft_content,
                target_entity=target_entity,
                context_summary=context_summary,
                confidence_score=confidence_score,
                entity_model_used=entity_model_used,
                expiration_hours=48,
            )

            added_item = mock_session.add.call_args[0][0]
            assert added_item.interaction_id == interaction_id
            assert added_item.draft_content == draft_content
            assert added_item.target_entity == target_entity
            assert added_item.context_summary == context_summary
            assert added_item.confidence_score == confidence_score
            assert added_item.entity_model_used == entity_model_used
            assert added_item.expires_at is not None


class TestApproveItem:
    """Tests for approve_item function."""

    @pytest.mark.asyncio
    async def test_approve_item_updates_status(self) -> None:
        """Should update item status to approved."""
        item_id = str(uuid4())

        # Create mock item
        mock_item = MagicMock()
        mock_item.id = item_id
        mock_item.status = ApprovalStatus.PENDING.value
        mock_item.draft_content = "Original draft"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_item)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch(
            "kairix_agent.social.approval_service._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.social import approval_service

            result = await approval_service.approve_item(item_id)

            assert result is not None
            assert mock_item.status == ApprovalStatus.APPROVED.value
            assert mock_item.reviewed_at is not None

    @pytest.mark.asyncio
    async def test_approve_item_with_modified_content(self) -> None:
        """Should update draft content when user modifies it."""
        item_id = str(uuid4())
        modified_content = "Modified draft content by user"

        mock_item = MagicMock()
        mock_item.id = item_id
        mock_item.status = ApprovalStatus.PENDING.value
        mock_item.draft_content = "Original draft"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_item)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch(
            "kairix_agent.social.approval_service._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.social import approval_service

            await approval_service.approve_item(item_id, modified_content=modified_content)

            assert mock_item.draft_content == modified_content

    @pytest.mark.asyncio
    async def test_approve_item_not_found(self) -> None:
        """Should return None when item not found."""
        item_id = str(uuid4())

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "kairix_agent.social.approval_service._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.social import approval_service

            result = await approval_service.approve_item(item_id)

            assert result is None

    @pytest.mark.asyncio
    async def test_approve_already_processed_item(self) -> None:
        """Should return item without changes if already processed."""
        item_id = str(uuid4())

        mock_item = MagicMock()
        mock_item.id = item_id
        mock_item.status = ApprovalStatus.APPROVED.value  # Already approved

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_item)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "kairix_agent.social.approval_service._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.social import approval_service

            result = await approval_service.approve_item(item_id)

            assert result is mock_item
            # Commit should not have been called since no changes
            mock_session.commit.assert_not_called()


class TestRejectItem:
    """Tests for reject_item function."""

    @pytest.mark.asyncio
    async def test_reject_item_updates_status(self) -> None:
        """Should update item status to rejected."""
        item_id = str(uuid4())

        mock_item = MagicMock()
        mock_item.id = item_id
        mock_item.status = ApprovalStatus.PENDING.value

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_item)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch(
            "kairix_agent.social.approval_service._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.social import approval_service

            result = await approval_service.reject_item(item_id)

            assert result is not None
            assert mock_item.status == ApprovalStatus.REJECTED.value
            assert mock_item.reviewed_at is not None

    @pytest.mark.asyncio
    async def test_reject_item_stores_feedback(self) -> None:
        """Should store user feedback on rejection."""
        item_id = str(uuid4())
        feedback = "Too promotional, be more conversational"

        mock_item = MagicMock()
        mock_item.id = item_id
        mock_item.status = ApprovalStatus.PENDING.value
        mock_item.user_feedback = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_item)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch(
            "kairix_agent.social.approval_service._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.social import approval_service

            await approval_service.reject_item(item_id, feedback=feedback)

            assert mock_item.user_feedback == feedback


class TestListPendingItems:
    """Tests for list_pending_items function."""

    @pytest.mark.asyncio
    async def test_list_pending_items(self) -> None:
        """Should return list of pending items."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"

        mock_items = [MagicMock(id=str(uuid4())) for _ in range(3)]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "kairix_agent.social.approval_service._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.social import approval_service

            result = await approval_service.list_pending_items(agent_id)

            assert len(result) == 3
            mock_session.execute.assert_called_once()


class TestGetQueueStats:
    """Tests for get_queue_stats function."""

    @pytest.mark.asyncio
    async def test_get_queue_stats(self) -> None:
        """Should return correct statistics."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"

        # Mock different query results for each status
        def make_mock_result(count: int) -> MagicMock:
            mock_scalars = MagicMock()
            mock_scalars.all = MagicMock(return_value=[MagicMock() for _ in range(count)])
            mock_result = MagicMock()
            mock_result.scalars = MagicMock(return_value=mock_scalars)
            return mock_result

        # Will be called 4 times: pending, approved, rejected, expired
        execute_returns = [
            make_mock_result(5),   # pending
            make_mock_result(10),  # approved
            make_mock_result(3),   # rejected
            make_mock_result(2),   # expired
        ]

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(side_effect=execute_returns)

        with patch(
            "kairix_agent.social.approval_service._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.social import approval_service

            stats = await approval_service.get_queue_stats(agent_id)

            assert stats["pending"] == 5
            assert stats["approved"] == 10
            assert stats["rejected"] == 3
            assert stats["expired"] == 2
            assert stats["total"] == 20
            # approval_rate = approved / (approved + rejected) = 10 / 13
            expected_rate = 10 / 13
            assert abs(stats["approval_rate"] - expected_rate) < 0.01

    @pytest.mark.asyncio
    async def test_get_queue_stats_empty_queue(self) -> None:
        """Should handle empty queue correctly."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"

        def make_empty_result() -> MagicMock:
            mock_scalars = MagicMock()
            mock_scalars.all = MagicMock(return_value=[])
            mock_result = MagicMock()
            mock_result.scalars = MagicMock(return_value=mock_scalars)
            return mock_result

        execute_returns = [make_empty_result() for _ in range(4)]

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(side_effect=execute_returns)

        with patch(
            "kairix_agent.social.approval_service._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.social import approval_service

            stats = await approval_service.get_queue_stats(agent_id)

            assert stats["total"] == 0
            assert stats["approval_rate"] == 0.0


class TestExpireOldItems:
    """Tests for expire_old_items function."""

    @pytest.mark.asyncio
    async def test_expire_old_items(self) -> None:
        """Should mark expired items as expired."""
        mock_result = MagicMock()
        mock_result.rowcount = 3

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with patch(
            "kairix_agent.social.approval_service._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.social import approval_service

            expired_count = await approval_service.expire_old_items()

            assert expired_count == 3
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()
