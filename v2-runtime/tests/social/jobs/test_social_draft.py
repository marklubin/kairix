"""Tests for social draft job."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestCleanDraft:
    """Tests for _clean_draft function."""

    def test_removes_meta_text_heres_my_draft(self) -> None:
        """Should remove 'here's my draft' prefix."""
        from kairix_agent.worker.jobs.social_draft import _clean_draft

        draft = "Here's my draft:\n\nActual content here"
        result = _clean_draft(draft)
        assert result == "Actual content here"

    def test_removes_meta_text_draft_prefix(self) -> None:
        """Should skip entire line starting with 'Draft:'."""
        from kairix_agent.worker.jobs.social_draft import _clean_draft

        # When the prefix line is followed by actual content
        draft = "Draft:\n\nThis is the response"
        result = _clean_draft(draft)
        assert result == "This is the response"

    def test_removes_meta_text_response_prefix(self) -> None:
        """Should skip entire line starting with 'Response:'."""
        from kairix_agent.worker.jobs.social_draft import _clean_draft

        draft = "Response:\n\nHere is what I would say"
        result = _clean_draft(draft)
        assert result == "Here is what I would say"

    def test_removes_meta_text_reply_prefix(self) -> None:
        """Should skip entire line starting with 'Reply:'."""
        from kairix_agent.worker.jobs.social_draft import _clean_draft

        draft = "Reply:\n\nI agree with this point"
        result = _clean_draft(draft)
        assert result == "I agree with this point"

    def test_preserves_normal_content(self) -> None:
        """Should preserve content without meta-text."""
        from kairix_agent.worker.jobs.social_draft import _clean_draft

        draft = "Great point! I've been thinking about this topic too."
        result = _clean_draft(draft)
        assert result == draft

    def test_removes_leading_empty_lines(self) -> None:
        """Should remove leading empty lines."""
        from kairix_agent.worker.jobs.social_draft import _clean_draft

        draft = "\n\n\nActual content"
        result = _clean_draft(draft)
        assert result == "Actual content"

    def test_removes_trailing_empty_lines(self) -> None:
        """Should remove trailing empty lines."""
        from kairix_agent.worker.jobs.social_draft import _clean_draft

        draft = "Content here\n\n\n"
        result = _clean_draft(draft)
        assert result == "Content here"

    def test_preserves_multiline_content(self) -> None:
        """Should preserve legitimate multiline content."""
        from kairix_agent.worker.jobs.social_draft import _clean_draft

        draft = "First paragraph.\n\nSecond paragraph."
        result = _clean_draft(draft)
        assert result == draft

    def test_handles_empty_string(self) -> None:
        """Should handle empty string."""
        from kairix_agent.worker.jobs.social_draft import _clean_draft

        result = _clean_draft("")
        assert result == ""

    def test_handles_whitespace_only(self) -> None:
        """Should handle whitespace-only string."""
        from kairix_agent.worker.jobs.social_draft import _clean_draft

        result = _clean_draft("   \n\n   ")
        assert result == ""


class TestBuildContextSummary:
    """Tests for _build_context_summary function."""

    def test_includes_interaction_type(self) -> None:
        """Should include interaction type in summary."""
        from kairix_agent.worker.jobs.social_draft import _build_context_summary

        mock_interaction = MagicMock()
        mock_interaction.interaction_type = "mention_received"
        mock_interaction.external_author = "user.bsky.social"
        mock_interaction.parent_post_id = None

        result = _build_context_summary(mock_interaction, "")
        assert "mention_received" in result

    def test_includes_author(self) -> None:
        """Should include author in summary."""
        from kairix_agent.worker.jobs.social_draft import _build_context_summary

        mock_interaction = MagicMock()
        mock_interaction.interaction_type = "mention_received"
        mock_interaction.external_author = "researcher.bsky.social"
        mock_interaction.parent_post_id = None

        result = _build_context_summary(mock_interaction, "")
        assert "researcher.bsky.social" in result

    def test_includes_reply_context(self) -> None:
        """Should note when it's a reply."""
        from kairix_agent.worker.jobs.social_draft import _build_context_summary

        mock_interaction = MagicMock()
        mock_interaction.interaction_type = "mention_received"
        mock_interaction.external_author = "user.bsky.social"
        mock_interaction.parent_post_id = "at://did:plc:parent/post-123"

        result = _build_context_summary(mock_interaction, "")
        assert "Reply" in result or "reply" in result

    def test_includes_truncated_reasoning(self) -> None:
        """Should include truncated evaluation reasoning."""
        from kairix_agent.worker.jobs.social_draft import _build_context_summary

        mock_interaction = MagicMock()
        mock_interaction.interaction_type = "mention_received"
        mock_interaction.external_author = "user.bsky.social"
        mock_interaction.parent_post_id = None

        long_reasoning = "A" * 300  # Longer than 200 char limit
        result = _build_context_summary(mock_interaction, long_reasoning)

        # Should include part of reasoning
        assert "A" * 50 in result
        # But not the full 300 chars (truncated at 200)
        assert len(result) < 350


class TestSocialDraftJob:
    """Tests for the social_draft job function."""

    @pytest.mark.asyncio
    async def test_draft_interaction_not_found(self) -> None:
        """Should return not_found when interaction doesn't exist."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"
        channel_id = str(uuid4())
        interaction_id = str(uuid4())

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_ctx: dict[str, object] = {}

        with patch(
            "kairix_agent.worker.jobs.social_draft._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.worker.jobs.social_draft import social_draft

            result = await social_draft(
                mock_ctx,
                agent_id=agent_id,
                channel_id=channel_id,
                interaction_id=interaction_id,
            )

            assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_draft_channel_not_found(self) -> None:
        """Should return channel_not_found when channel doesn't exist."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"
        channel_id = str(uuid4())
        interaction_id = str(uuid4())

        mock_interaction = MagicMock()
        mock_interaction.id = interaction_id

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

        mock_ctx: dict[str, object] = {}

        with patch(
            "kairix_agent.worker.jobs.social_draft._async_session",
            return_value=mock_session,
        ):
            from kairix_agent.worker.jobs.social_draft import social_draft

            result = await social_draft(
                mock_ctx,
                agent_id=agent_id,
                channel_id=channel_id,
                interaction_id=interaction_id,
            )

            assert result["status"] == "channel_not_found"

    @pytest.mark.asyncio
    async def test_draft_creates_approval_item(self) -> None:
        """Should create approval queue item with draft."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"
        channel_id = str(uuid4())
        interaction_id = str(uuid4())
        approval_item_id = str(uuid4())

        mock_interaction = MagicMock()
        mock_interaction.id = interaction_id
        mock_interaction.content_text = "What do you think about AI memory?"
        mock_interaction.external_author = "researcher.bsky.social"
        mock_interaction.external_author_did = "did:plc:researcher"
        mock_interaction.interaction_type = "mention_received"
        mock_interaction.parent_post_id = None

        mock_channel = MagicMock()
        mock_channel.id = channel_id
        mock_channel.channel_type = "bluesky"
        mock_channel.engagement_level = "moderate"
        mock_channel.trust_level = "learning"

        mock_result_interaction = MagicMock()
        mock_result_interaction.scalar_one_or_none = MagicMock(return_value=mock_interaction)

        mock_result_channel = MagicMock()
        mock_result_channel.scalar_one_or_none = MagicMock(return_value=mock_channel)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(
            side_effect=[mock_result_interaction, mock_result_channel]
        )

        mock_ctx: dict[str, object] = {}

        mock_block_agent = AsyncMock()
        mock_block_agent.run = AsyncMock(
            return_value="Great question! AI memory systems are fascinating."
        )

        mock_approval_item = MagicMock()
        mock_approval_item.id = approval_item_id

        with (
            patch(
                "kairix_agent.worker.jobs.social_draft._async_session",
                return_value=mock_session,
            ),
            patch(
                "kairix_agent.worker.jobs.social_draft.BlockManagerAgent",
                return_value=mock_block_agent,
            ),
            patch("kairix_agent.worker.jobs.social_draft.AsyncLetta"),
            patch(
                "kairix_agent.worker.jobs.social_draft.approval_service.create_approval_item",
                new_callable=AsyncMock,
                return_value=mock_approval_item,
            ) as mock_create_approval,
            patch(
                "kairix_agent.worker.jobs.social_draft.publish_event",
                new_callable=AsyncMock,
            ),
        ):
            from kairix_agent.worker.jobs.social_draft import social_draft

            result = await social_draft(
                mock_ctx,
                agent_id=agent_id,
                channel_id=channel_id,
                interaction_id=interaction_id,
            )

            assert result["status"] == "ok"
            assert result["approval_item_id"] == approval_item_id

            # Verify approval item was created
            mock_create_approval.assert_called_once()
            call_kwargs = mock_create_approval.call_args[1]
            assert call_kwargs["agent_id"] == agent_id
            assert call_kwargs["channel_type"] == "bluesky"
            assert "AI memory" in call_kwargs["draft_content"]

    @pytest.mark.asyncio
    async def test_draft_empty_returns_error(self) -> None:
        """Should return empty_draft status when LLM returns empty."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"
        channel_id = str(uuid4())
        interaction_id = str(uuid4())

        mock_interaction = MagicMock()
        mock_interaction.id = interaction_id
        mock_interaction.content_text = "Test"
        mock_interaction.external_author = "user.bsky.social"
        mock_interaction.external_author_did = "did:plc:user"
        mock_interaction.interaction_type = "mention_received"
        mock_interaction.parent_post_id = None

        mock_channel = MagicMock()
        mock_channel.id = channel_id
        mock_channel.channel_type = "bluesky"
        mock_channel.engagement_level = "moderate"
        mock_channel.trust_level = "learning"

        mock_result_interaction = MagicMock()
        mock_result_interaction.scalar_one_or_none = MagicMock(return_value=mock_interaction)

        mock_result_channel = MagicMock()
        mock_result_channel.scalar_one_or_none = MagicMock(return_value=mock_channel)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(
            side_effect=[mock_result_interaction, mock_result_channel]
        )

        mock_ctx: dict[str, object] = {}

        mock_block_agent = AsyncMock()
        mock_block_agent.run = AsyncMock(return_value="")  # Empty response

        with (
            patch(
                "kairix_agent.worker.jobs.social_draft._async_session",
                return_value=mock_session,
            ),
            patch(
                "kairix_agent.worker.jobs.social_draft.BlockManagerAgent",
                return_value=mock_block_agent,
            ),
            patch("kairix_agent.worker.jobs.social_draft.AsyncLetta"),
        ):
            from kairix_agent.worker.jobs.social_draft import social_draft

            result = await social_draft(
                mock_ctx,
                agent_id=agent_id,
                channel_id=channel_id,
                interaction_id=interaction_id,
            )

            assert result["status"] == "empty_draft"

    @pytest.mark.asyncio
    async def test_draft_respects_trust_level(self) -> None:
        """Should set needs_approval based on trust level."""
        agent_id = f"test-agent-{uuid4().hex[:8]}"
        channel_id = str(uuid4())
        interaction_id = str(uuid4())

        mock_interaction = MagicMock()
        mock_interaction.id = interaction_id
        mock_interaction.content_text = "Test"
        mock_interaction.external_author = "user.bsky.social"
        mock_interaction.external_author_did = "did:plc:user"
        mock_interaction.interaction_type = "mention_received"
        mock_interaction.parent_post_id = None

        # Channel with LEARNING trust level requires approval
        mock_channel = MagicMock()
        mock_channel.id = channel_id
        mock_channel.channel_type = "bluesky"
        mock_channel.engagement_level = "moderate"
        mock_channel.trust_level = "learning"

        mock_result_interaction = MagicMock()
        mock_result_interaction.scalar_one_or_none = MagicMock(return_value=mock_interaction)

        mock_result_channel = MagicMock()
        mock_result_channel.scalar_one_or_none = MagicMock(return_value=mock_channel)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(
            side_effect=[mock_result_interaction, mock_result_channel]
        )

        mock_ctx: dict[str, object] = {}

        mock_block_agent = AsyncMock()
        mock_block_agent.run = AsyncMock(return_value="Draft response")

        mock_approval_item = MagicMock()
        mock_approval_item.id = str(uuid4())

        with (
            patch(
                "kairix_agent.worker.jobs.social_draft._async_session",
                return_value=mock_session,
            ),
            patch(
                "kairix_agent.worker.jobs.social_draft.BlockManagerAgent",
                return_value=mock_block_agent,
            ),
            patch("kairix_agent.worker.jobs.social_draft.AsyncLetta"),
            patch(
                "kairix_agent.worker.jobs.social_draft.approval_service.create_approval_item",
                new_callable=AsyncMock,
                return_value=mock_approval_item,
            ),
            patch(
                "kairix_agent.worker.jobs.social_draft.publish_event",
                new_callable=AsyncMock,
            ),
        ):
            from kairix_agent.worker.jobs.social_draft import social_draft

            result = await social_draft(
                mock_ctx,
                agent_id=agent_id,
                channel_id=channel_id,
                interaction_id=interaction_id,
            )

            # Learning trust level means approval is needed
            assert result["needs_approval"] is True
