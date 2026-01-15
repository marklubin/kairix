"""Tests for social evaluation job."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestParseEngagementDecision:
    """Tests for _parse_engagement_decision function."""

    def test_explicit_engage_yes(self) -> None:
        """Should return True for explicit 'engage: yes'."""
        from kairix_agent.worker.jobs.social_evaluate import _parse_engagement_decision

        assert _parse_engagement_decision("ENGAGE: yes") is True
        assert _parse_engagement_decision("engage: yes") is True
        assert _parse_engagement_decision("Based on analysis, ENGAGE: yes") is True

    def test_explicit_engage_no(self) -> None:
        """Should return False for explicit 'engage: no'."""
        from kairix_agent.worker.jobs.social_evaluate import _parse_engagement_decision

        assert _parse_engagement_decision("ENGAGE: no") is False
        assert _parse_engagement_decision("engage: no") is False
        assert _parse_engagement_decision("After consideration, engage: no") is False

    def test_should_engage_true(self) -> None:
        """Should return True for 'should_engage: true'."""
        from kairix_agent.worker.jobs.social_evaluate import _parse_engagement_decision

        assert _parse_engagement_decision("should_engage: true") is True
        assert _parse_engagement_decision("Decision: should_engage: true") is True

    def test_should_engage_false(self) -> None:
        """Should return False for 'should_engage: false'."""
        from kairix_agent.worker.jobs.social_evaluate import _parse_engagement_decision

        assert _parse_engagement_decision("should_engage: false") is False

    def test_positive_signals(self) -> None:
        """Should return True for positive signal phrases."""
        from kairix_agent.worker.jobs.social_evaluate import _parse_engagement_decision

        assert _parse_engagement_decision("I recommend engaging with this post") is True
        assert _parse_engagement_decision("This is worth responding to") is True
        assert _parse_engagement_decision("We should respond to this") is True
        assert _parse_engagement_decision("Let's engage with this post") is True

    def test_negative_signals(self) -> None:
        """Should return False for negative signal phrases."""
        from kairix_agent.worker.jobs.social_evaluate import _parse_engagement_decision

        assert _parse_engagement_decision("Let's skip this one") is False
        assert _parse_engagement_decision("I don't think we should engage") is False
        assert _parse_engagement_decision("Not worth our time") is False
        assert _parse_engagement_decision("We should ignore this") is False
        assert _parse_engagement_decision("Better to pass on this one") is False

    def test_default_conservative(self) -> None:
        """Should default to False when no clear signals."""
        from kairix_agent.worker.jobs.social_evaluate import _parse_engagement_decision

        assert _parse_engagement_decision("This is an interesting post about AI.") is False
        assert _parse_engagement_decision("The author makes good points.") is False
        assert _parse_engagement_decision("") is False


class TestSocialEvaluateJob:
    """Tests for the social_evaluate job function."""

    @pytest.mark.asyncio
    async def test_evaluate_interaction_not_found(self) -> None:
        """Should return not_found status when interaction doesn't exist."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"
        channel_id = str(uuid4())
        interaction_id = str(uuid4())

        # Mock session that returns None for interaction
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_queue = AsyncMock()
        mock_ctx = {"queue": mock_queue}

        with patch(
            "kairix_agent.worker.jobs.social_evaluate._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.worker.jobs.social_evaluate import social_evaluate

            result = await social_evaluate(
                mock_ctx,
                agent_id=agent_id,
                channel_id=channel_id,
                interaction_id=interaction_id,
            )

            assert result["status"] == "not_found"
            assert result["interaction_id"] == interaction_id

    @pytest.mark.asyncio
    async def test_evaluate_channel_not_found(self) -> None:
        """Should return channel_not_found when channel doesn't exist."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"
        channel_id = str(uuid4())
        interaction_id = str(uuid4())

        # Mock interaction
        mock_interaction = MagicMock()
        mock_interaction.id = interaction_id
        mock_interaction.content_text = "Test post"
        mock_interaction.external_author = "author.bsky.social"

        # First call returns interaction, second returns None (no channel)
        mock_result_interaction = MagicMock()
        mock_result_interaction.scalar_one_or_none = MagicMock(return_value=mock_interaction)

        mock_result_channel = MagicMock()
        mock_result_channel.scalar_one_or_none = MagicMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(
            side_effect=[mock_result_interaction, mock_result_channel]
        )

        mock_queue = AsyncMock()
        mock_ctx = {"queue": mock_queue}

        with patch(
            "kairix_agent.worker.jobs.social_evaluate._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.worker.jobs.social_evaluate import social_evaluate

            result = await social_evaluate(
                mock_ctx,
                agent_id=agent_id,
                channel_id=channel_id,
                interaction_id=interaction_id,
            )

            assert result["status"] == "channel_not_found"

    @pytest.mark.asyncio
    async def test_evaluate_uses_block_manager_agent(self) -> None:
        """Should use BlockManagerAgent for evaluation."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"
        channel_id = str(uuid4())
        interaction_id = str(uuid4())

        # Mock interaction
        mock_interaction = MagicMock()
        mock_interaction.id = interaction_id
        mock_interaction.content_text = "Interesting post about AI memory systems"
        mock_interaction.external_author = "researcher.bsky.social"
        mock_interaction.external_author_did = "did:plc:researcher"
        mock_interaction.interaction_type = "mention_received"
        mock_interaction.parent_post_id = None
        mock_interaction.thread_root_id = None
        mock_interaction.extra_data = {}

        # Mock channel
        mock_channel = MagicMock()
        mock_channel.id = channel_id
        mock_channel.channel_type = "bluesky"
        mock_channel.engagement_level = "moderate"
        mock_channel.trust_level = "learning"

        # Setup query results
        mock_result_interaction = MagicMock()
        mock_result_interaction.scalar_one_or_none = MagicMock(return_value=mock_interaction)

        mock_result_channel = MagicMock()
        mock_result_channel.scalar_one_or_none = MagicMock(return_value=mock_channel)

        mock_result_trigger = MagicMock()
        mock_result_trigger.scalar_one_or_none = MagicMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(
            side_effect=[mock_result_interaction, mock_result_channel, mock_result_trigger]
        )

        mock_queue = AsyncMock()
        mock_ctx = {"queue": mock_queue}

        # Mock BlockManagerAgent
        mock_block_agent = AsyncMock()
        mock_block_agent.run = AsyncMock(return_value="ENGAGE: yes\nThis is relevant.")

        with (
            patch(
                "kairix_agent.worker.jobs.social_evaluate._async_session",
                return_value=mock_session,
            ),
            patch(
                "kairix_agent.worker.jobs.social_evaluate.BlockManagerAgent",
                return_value=mock_block_agent,
            ),
            patch(
                "kairix_agent.worker.jobs.social_evaluate.AsyncLetta",
            ) as mock_letta_class,
        ):
            mock_letta_class.return_value = AsyncMock()

            from kairix_agent.worker.jobs.social_evaluate import social_evaluate

            result = await social_evaluate(
                mock_ctx,
                agent_id=agent_id,
                channel_id=channel_id,
                interaction_id=interaction_id,
                is_mention=True,
            )

            assert result["status"] == "ok"
            assert result["should_engage"] is True
            assert result["draft_enqueued"] is True

            # Verify BlockManagerAgent.run was called
            mock_block_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_engage_yes_enqueues_draft(self) -> None:
        """Should enqueue draft job when decision is to engage."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"
        channel_id = str(uuid4())
        interaction_id = str(uuid4())

        # Mock interaction and channel
        mock_interaction = MagicMock()
        mock_interaction.id = interaction_id
        mock_interaction.content_text = "Test"
        mock_interaction.external_author = "user.bsky.social"
        mock_interaction.external_author_did = "did:plc:user"
        mock_interaction.interaction_type = "mention_received"
        mock_interaction.parent_post_id = None
        mock_interaction.thread_root_id = None
        mock_interaction.extra_data = {}

        mock_channel = MagicMock()
        mock_channel.id = channel_id
        mock_channel.agent_id = agent_id
        mock_channel.channel_type = "bluesky"
        mock_channel.engagement_level = "moderate"
        mock_channel.trust_level = "learning"

        mock_result_interaction = MagicMock()
        mock_result_interaction.scalar_one_or_none = MagicMock(return_value=mock_interaction)

        mock_result_channel = MagicMock()
        mock_result_channel.scalar_one_or_none = MagicMock(return_value=mock_channel)

        mock_result_trigger = MagicMock()
        mock_result_trigger.scalar_one_or_none = MagicMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(
            side_effect=[mock_result_interaction, mock_result_channel, mock_result_trigger]
        )

        mock_queue = AsyncMock()
        mock_ctx = {"queue": mock_queue}

        mock_block_agent = AsyncMock()
        mock_block_agent.run = AsyncMock(return_value="ENGAGE: yes")

        with (
            patch(
                "kairix_agent.worker.jobs.social_evaluate._async_session",
                return_value=mock_session,
            ),
            patch(
                "kairix_agent.worker.jobs.social_evaluate.BlockManagerAgent",
                return_value=mock_block_agent,
            ),
            patch("kairix_agent.worker.jobs.social_evaluate.AsyncLetta"),
        ):
            from kairix_agent.worker.jobs.social_evaluate import social_evaluate

            result = await social_evaluate(
                mock_ctx,
                agent_id=agent_id,
                channel_id=channel_id,
                interaction_id=interaction_id,
            )

            assert result["draft_enqueued"] is True

            # Verify draft job was enqueued
            mock_queue.enqueue.assert_called_once()
            call_args = mock_queue.enqueue.call_args
            assert call_args[0][0] == "social_draft"
            assert call_args[1]["agent_id"] == agent_id
            assert call_args[1]["channel_id"] == channel_id
            assert call_args[1]["interaction_id"] == interaction_id

    @pytest.mark.asyncio
    async def test_evaluate_engage_no_skips_draft(self) -> None:
        """Should not enqueue draft job when decision is not to engage."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"
        channel_id = str(uuid4())
        interaction_id = str(uuid4())

        mock_interaction = MagicMock()
        mock_interaction.id = interaction_id
        mock_interaction.content_text = "Spam post"
        mock_interaction.external_author = "spammer.bsky.social"
        mock_interaction.external_author_did = "did:plc:spammer"
        mock_interaction.interaction_type = "timeline_view"
        mock_interaction.parent_post_id = None
        mock_interaction.thread_root_id = None
        mock_interaction.extra_data = {}

        mock_channel = MagicMock()
        mock_channel.id = channel_id
        mock_channel.channel_type = "bluesky"
        mock_channel.engagement_level = "conservative"
        mock_channel.trust_level = "learning"

        mock_result_interaction = MagicMock()
        mock_result_interaction.scalar_one_or_none = MagicMock(return_value=mock_interaction)

        mock_result_channel = MagicMock()
        mock_result_channel.scalar_one_or_none = MagicMock(return_value=mock_channel)

        mock_result_trigger = MagicMock()
        mock_result_trigger.scalar_one_or_none = MagicMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(
            side_effect=[mock_result_interaction, mock_result_channel, mock_result_trigger]
        )

        mock_queue = AsyncMock()
        mock_ctx = {"queue": mock_queue}

        mock_block_agent = AsyncMock()
        mock_block_agent.run = AsyncMock(return_value="ENGAGE: no\nNot relevant.")

        with (
            patch(
                "kairix_agent.worker.jobs.social_evaluate._async_session",
                return_value=mock_session,
            ),
            patch(
                "kairix_agent.worker.jobs.social_evaluate.BlockManagerAgent",
                return_value=mock_block_agent,
            ),
            patch("kairix_agent.worker.jobs.social_evaluate.AsyncLetta"),
        ):
            from kairix_agent.worker.jobs.social_evaluate import social_evaluate

            result = await social_evaluate(
                mock_ctx,
                agent_id=agent_id,
                channel_id=channel_id,
                interaction_id=interaction_id,
            )

            assert result["should_engage"] is False
            assert result["draft_enqueued"] is False
            mock_queue.enqueue.assert_not_called()
