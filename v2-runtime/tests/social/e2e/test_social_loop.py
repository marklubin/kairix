"""End-to-end integration tests for the social agent loop.

These tests use a REAL PostgreSQL database (via ./kx dev) while mocking:
- External services (Bluesky API via atproto)
- LLM calls (BlockManagerAgent)
- Job queue (SAQ)
- Event publishing

Run these tests with:
    ./kx dev && ./kx wait postgres && ./kx migrate
    uv run pytest tests/social/e2e/ -v -m integration

Flow tested:
1. Create real channel in database
2. Explore (mock external timeline data, real DB storage)
3. Evaluate triggers (real trigger lookup from DB)
4. Draft response (mock LLM, real approval queue in DB)
5. Approve/reject (real DB operations)
6. Verify state changes in real database
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from kairix_agent.social.models import (
    ActionType,
    ApprovalStatus,
    InteractionType,
)

if TYPE_CHECKING:
    from kairix_agent.social.models import SocialChannel


# =============================================================================
# Integration Test: Full Social Loop with Real Database
# =============================================================================


@pytest.mark.integration
class TestSocialLoopIntegration:
    """Integration tests using real database operations."""

    @pytest.mark.asyncio
    async def test_explore_stores_interactions_in_real_db(
        self,
        test_channel: SocialChannel,
        test_encryption_key: str,
        mock_bluesky_client: MagicMock,
        mock_saq_context: dict[str, object],
    ) -> None:
        """Exploration job should store interactions in real database."""
        from kairix_agent.social.channels.base import SocialPost
        from kairix_agent.social.crypto import get_fernet

        # Create mock posts
        mock_posts = [
            SocialPost(
                external_id=f"at://did:plc:test/post-{i}",
                author_handle=f"user{i}.bsky.social",
                author_display_name=f"User {i}",
                author_did=f"did:plc:user{i}",
                content=f"Integration test post content {i}",
                created_at=datetime.now(UTC),
                reply_count=i,
                repost_count=i,
                like_count=i * 10,
            )
            for i in range(5)
        ]

        # Mock social channel implementation
        mock_social_channel = AsyncMock()
        mock_social_channel.authenticate = AsyncMock(return_value=True)
        mock_social_channel.get_timeline = AsyncMock(return_value=(mock_posts, "cursor"))
        mock_social_channel.get_mentions = AsyncMock(return_value=[])

        with (
            patch(
                "kairix_agent.worker.jobs.social_explore.create_channel",
                return_value=mock_social_channel,
            ),
            patch(
                "kairix_agent.worker.jobs.social_explore.publish_event",
                new_callable=AsyncMock,
            ),
            patch("kairix_agent.social.crypto.Config") as mock_config,
        ):
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = test_encryption_key
            get_fernet.cache_clear()

            try:
                from kairix_agent.worker.jobs.social_explore import social_explore

                result = await social_explore(
                    mock_saq_context,
                    channel_id=str(test_channel.id),
                )

                assert result["status"] == "ok"

                # Verify interactions were stored in REAL database
                from kairix_agent.social import service

                interactions = await service.list_interactions(str(test_channel.id))
                assert len(interactions) >= 5

                # Verify content matches
                contents = {i.content_text for i in interactions}
                for i in range(5):
                    assert f"Integration test post content {i}" in contents
            finally:
                get_fernet.cache_clear()

    @pytest.mark.asyncio
    async def test_mention_triggers_evaluate_job_with_real_triggers(
        self,
        test_channel: SocialChannel,
        test_encryption_key: str,
        mock_saq_queue: AsyncMock,
    ) -> None:
        """Direct mention should trigger evaluation using real DB triggers."""
        from kairix_agent.social.channels.base import SocialPost
        from kairix_agent.social.crypto import get_fernet

        # Create a mention post
        mention_post = SocialPost(
            external_id="at://did:plc:mentioner/mention-post",
            author_handle="mentioner.bsky.social",
            author_display_name="Mentioner",
            author_did="did:plc:mentioner",
            content=f"Hey @{test_channel.handle} what do you think about AI?",
            created_at=datetime.now(UTC),
            reply_count=0,
            repost_count=0,
            like_count=0,
        )

        mock_social_channel = AsyncMock()
        mock_social_channel.authenticate = AsyncMock(return_value=True)
        mock_social_channel.get_timeline = AsyncMock(return_value=([], None))
        mock_social_channel.get_mentions = AsyncMock(return_value=[mention_post])

        with (
            patch(
                "kairix_agent.worker.jobs.social_explore.create_channel",
                return_value=mock_social_channel,
            ),
            patch(
                "kairix_agent.worker.jobs.social_explore.publish_event",
                new_callable=AsyncMock,
            ),
            patch("kairix_agent.social.crypto.Config") as mock_config,
        ):
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = test_encryption_key
            get_fernet.cache_clear()

            try:
                from kairix_agent.worker.jobs.social_explore import social_explore

                result = await social_explore(
                    {"queue": mock_saq_queue},
                    channel_id=str(test_channel.id),
                )

                assert result["status"] == "ok"

                # Should have enqueued evaluate job
                # (test_channel fixture creates default direct_mention trigger)
                assert mock_saq_queue.enqueue.call_count >= 1

                # Check that social_evaluate was enqueued
                enqueue_calls = mock_saq_queue.enqueue.call_args_list
                evaluate_calls = [
                    call for call in enqueue_calls if call[0][0] == "social_evaluate"
                ]
                assert len(evaluate_calls) >= 1
            finally:
                get_fernet.cache_clear()

    @pytest.mark.asyncio
    async def test_draft_creates_real_approval_item(
        self,
        test_channel: SocialChannel,
        test_encryption_key: str,
        mock_block_manager_responses: dict[str, str],
    ) -> None:
        """Draft job should create a real approval queue item in database."""
        from kairix_agent.social import service
        from kairix_agent.social.channels.base import SocialPost
        from kairix_agent.social.crypto import get_fernet

        # First, create a real interaction in the database
        mock_post = SocialPost(
            external_id=f"at://did:plc:test/post-{uuid4().hex[:8]}",
            author_handle="asker.bsky.social",
            author_display_name="Asker",
            author_did="did:plc:asker",
            content="What do you think about memory systems?",
            created_at=datetime.now(UTC),
        )

        # Store interaction directly using the explore job's pattern
        mock_social_channel = AsyncMock()
        mock_social_channel.authenticate = AsyncMock(return_value=True)
        mock_social_channel.get_timeline = AsyncMock(return_value=([mock_post], None))
        mock_social_channel.get_mentions = AsyncMock(return_value=[])

        mock_queue = AsyncMock()

        with (
            patch(
                "kairix_agent.worker.jobs.social_explore.create_channel",
                return_value=mock_social_channel,
            ),
            patch(
                "kairix_agent.worker.jobs.social_explore.publish_event",
                new_callable=AsyncMock,
            ),
            patch("kairix_agent.social.crypto.Config") as mock_config,
        ):
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = test_encryption_key
            get_fernet.cache_clear()

            from kairix_agent.worker.jobs.social_explore import social_explore

            await social_explore(
                {"queue": mock_queue},
                channel_id=str(test_channel.id),
            )

        # Get the stored interaction
        interactions = await service.list_interactions(str(test_channel.id), limit=1)
        assert len(interactions) >= 1
        interaction = interactions[0]

        # Mock BlockManagerAgent
        mock_block_agent = AsyncMock()
        draft_content = "Great question! AI memory systems are fascinating."
        mock_block_agent.run = AsyncMock(return_value=draft_content)

        with (
            patch(
                "kairix_agent.worker.jobs.social_draft.BlockManagerAgent",
                return_value=mock_block_agent,
            ),
            patch("kairix_agent.worker.jobs.social_draft.AsyncLetta"),
            patch(
                "kairix_agent.worker.jobs.social_draft.publish_event",
                new_callable=AsyncMock,
            ),
            patch("kairix_agent.social.crypto.Config") as mock_config,
        ):
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = test_encryption_key
            get_fernet.cache_clear()

            try:
                from kairix_agent.worker.jobs.social_draft import social_draft

                result = await social_draft(
                    {},
                    agent_id=test_channel.agent_id,
                    channel_id=str(test_channel.id),
                    interaction_id=str(interaction.id),
                    evaluation_reasoning="Relevant post worth engaging with",
                )

                assert result["status"] == "ok"
                assert result["needs_approval"] is True
                approval_item_id = result["approval_item_id"]

                # Verify approval item exists in REAL database
                from kairix_agent.social import approval_service

                item = await approval_service.get_approval_item(approval_item_id)
                assert item is not None
                assert item.agent_id == test_channel.agent_id
                assert item.status == ApprovalStatus.PENDING.value
                assert "memory" in item.draft_content.lower()
            finally:
                get_fernet.cache_clear()

    @pytest.mark.asyncio
    async def test_approval_workflow_with_real_database(
        self,
        cleanup_agent: str,
        test_encryption_key: str,
    ) -> None:
        """User can approve/reject drafts using real database operations."""
        from kairix_agent.social import approval_service
        from kairix_agent.social.crypto import get_fernet

        with patch("kairix_agent.social.crypto.Config") as mock_config:
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = test_encryption_key
            get_fernet.cache_clear()

            try:
                # Create a real approval item
                item = await approval_service.create_approval_item(
                    agent_id=cleanup_agent,
                    channel_type="bluesky",
                    action_type=ActionType.REPLY,
                    draft_content="Test draft for integration test",
                    target_entity="@someone.bsky.social",
                    confidence_score=0.8,
                )

                # Verify it's pending
                pending = await approval_service.list_pending_items(cleanup_agent)
                assert len(pending) == 1
                assert str(pending[0].id) == str(item.id)

                # Approve with modification
                modified_content = "Modified draft content by user"
                approved = await approval_service.approve_item(
                    str(item.id),
                    modified_content=modified_content,
                )

                assert approved is not None
                assert approved.status == ApprovalStatus.APPROVED.value
                assert approved.draft_content == modified_content
                assert approved.reviewed_at is not None

                # Verify no longer pending
                pending = await approval_service.list_pending_items(cleanup_agent)
                assert len(pending) == 0
            finally:
                get_fernet.cache_clear()

    @pytest.mark.asyncio
    async def test_rejection_feedback_stored_in_real_database(
        self,
        cleanup_agent: str,
        test_encryption_key: str,
    ) -> None:
        """Rejection with feedback is recorded in real database."""
        from kairix_agent.social import approval_service
        from kairix_agent.social.crypto import get_fernet

        with patch("kairix_agent.social.crypto.Config") as mock_config:
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = test_encryption_key
            get_fernet.cache_clear()

            try:
                item = await approval_service.create_approval_item(
                    agent_id=cleanup_agent,
                    channel_type="bluesky",
                    action_type=ActionType.REPLY,
                    draft_content="Too promotional sounding",
                )

                feedback = "Too sales-y, be more conversational"
                rejected = await approval_service.reject_item(str(item.id), feedback=feedback)

                assert rejected is not None
                assert rejected.status == ApprovalStatus.REJECTED.value
                assert rejected.user_feedback == feedback

                # Verify stored in DB by re-fetching
                refetched = await approval_service.get_approval_item(str(item.id))
                assert refetched is not None
                assert refetched.user_feedback == feedback
            finally:
                get_fernet.cache_clear()

    @pytest.mark.asyncio
    async def test_queue_stats_with_real_data(
        self,
        cleanup_agent: str,
        test_encryption_key: str,
    ) -> None:
        """Queue statistics calculated from real database records."""
        from kairix_agent.social import approval_service
        from kairix_agent.social.crypto import get_fernet

        with patch("kairix_agent.social.crypto.Config") as mock_config:
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = test_encryption_key
            get_fernet.cache_clear()

            try:
                # Create several items in different states
                pending_item = await approval_service.create_approval_item(
                    agent_id=cleanup_agent,
                    channel_type="bluesky",
                    action_type=ActionType.REPLY,
                    draft_content="Pending item",
                )

                approved_item = await approval_service.create_approval_item(
                    agent_id=cleanup_agent,
                    channel_type="bluesky",
                    action_type=ActionType.REPLY,
                    draft_content="To be approved",
                )
                await approval_service.approve_item(str(approved_item.id))

                rejected_item = await approval_service.create_approval_item(
                    agent_id=cleanup_agent,
                    channel_type="bluesky",
                    action_type=ActionType.REPLY,
                    draft_content="To be rejected",
                )
                await approval_service.reject_item(str(rejected_item.id))

                # Get stats
                stats = await approval_service.get_queue_stats(cleanup_agent)

                assert stats["pending"] == 1
                assert stats["approved"] == 1
                assert stats["rejected"] == 1
                assert stats["total"] == 3
                # approval_rate = 1 / (1 + 1) = 0.5
                assert abs(stats["approval_rate"] - 0.5) < 0.01
            finally:
                get_fernet.cache_clear()


@pytest.mark.integration
class TestMultipleIterationsIntegration:
    """Test multiple loop iterations build up state correctly."""

    @pytest.mark.asyncio
    async def test_three_iterations_accumulate_interactions(
        self,
        test_channel: SocialChannel,
        test_encryption_key: str,
        mock_saq_queue: AsyncMock,
    ) -> None:
        """Running explore 3 times accumulates interactions in real DB."""
        from kairix_agent.social import service
        from kairix_agent.social.channels.base import SocialPost
        from kairix_agent.social.crypto import get_fernet

        with patch("kairix_agent.social.crypto.Config") as mock_config:
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = test_encryption_key
            get_fernet.cache_clear()

            try:
                for i in range(3):
                    # Create different posts each iteration
                    mock_posts = [
                        SocialPost(
                            external_id=f"at://did:plc:test/iter{i}-post-{j}",
                            author_handle=f"user{j}.bsky.social",
                            author_display_name=f"User {j}",
                            author_did=f"did:plc:user{j}",
                            content=f"Iteration {i} post {j}",
                            created_at=datetime.now(UTC),
                        )
                        for j in range(3)
                    ]

                    mock_social_channel = AsyncMock()
                    mock_social_channel.authenticate = AsyncMock(return_value=True)
                    mock_social_channel.get_timeline = AsyncMock(
                        return_value=(mock_posts, f"cursor-{i}")
                    )
                    mock_social_channel.get_mentions = AsyncMock(return_value=[])

                    with (
                        patch(
                            "kairix_agent.worker.jobs.social_explore.create_channel",
                            return_value=mock_social_channel,
                        ),
                        patch(
                            "kairix_agent.worker.jobs.social_explore.publish_event",
                            new_callable=AsyncMock,
                        ),
                    ):
                        from kairix_agent.worker.jobs.social_explore import social_explore

                        await social_explore(
                            {"queue": mock_saq_queue},
                            channel_id=str(test_channel.id),
                        )

                # Should have interactions from all 3 runs
                interactions = await service.list_interactions(
                    str(test_channel.id), limit=100
                )
                # 3 posts per iteration x 3 iterations = 9 interactions
                assert len(interactions) >= 9

                # Verify we have posts from all iterations
                contents = {i.content_text for i in interactions}
                for i in range(3):
                    for j in range(3):
                        assert f"Iteration {i} post {j}" in contents
            finally:
                get_fernet.cache_clear()


@pytest.mark.integration
class TestTriggerEvaluationIntegration:
    """Integration tests for trigger evaluation with real DB."""

    def test_direct_mention_trigger_matches(self) -> None:
        """Direct mention trigger should match mention posts."""
        from unittest.mock import MagicMock

        from kairix_agent.social.channels.base import SocialPost
        from kairix_agent.social.models import TriggerAction, TriggerType
        from kairix_agent.worker.jobs.social_explore import _evaluate_triggers

        trigger = MagicMock()
        trigger.id = str(uuid4())
        trigger.trigger_type = TriggerType.DIRECT_MENTION.value
        trigger.config = {}
        trigger.cooldown_minutes = 5
        trigger.last_fired_at = None
        trigger.enabled = True
        trigger.action = TriggerAction.WAKE_AND_EVALUATE.value
        triggers = [trigger]

        post = SocialPost(
            external_id="at://test/post",
            author_handle="user.bsky.social",
            author_display_name="User",
            author_did="did:plc:user",
            content="Test post",
            created_at=datetime.now(UTC),
        )

        # Direct mention should match
        matches = _evaluate_triggers(triggers, post, is_mention=True)
        assert len(matches) == 1
        assert matches[0][0] == trigger
        assert matches[0][1] == "direct_mention"

        # Non-mention should not match
        matches = _evaluate_triggers(triggers, post, is_mention=False)
        assert len(matches) == 0

    def test_keyword_trigger_matches_pattern(self) -> None:
        """Keyword trigger should match content patterns."""
        from unittest.mock import MagicMock

        from kairix_agent.social.channels.base import SocialPost
        from kairix_agent.social.models import TriggerAction, TriggerType
        from kairix_agent.worker.jobs.social_explore import _evaluate_triggers

        trigger = MagicMock()
        trigger.id = str(uuid4())
        trigger.trigger_type = TriggerType.KEYWORD.value
        trigger.config = {"pattern": "AI memory"}
        trigger.cooldown_minutes = 5
        trigger.last_fired_at = None
        trigger.enabled = True
        trigger.action = TriggerAction.WAKE_AND_EVALUATE.value
        triggers = [trigger]

        matching_post = SocialPost(
            external_id="at://test/post",
            author_handle="user.bsky.social",
            author_display_name="User",
            author_did="did:plc:user",
            content="Thinking about AI memory systems today",
            created_at=datetime.now(UTC),
        )

        non_matching_post = SocialPost(
            external_id="at://test/post2",
            author_handle="user.bsky.social",
            author_display_name="User",
            author_did="did:plc:user",
            content="Just had lunch",
            created_at=datetime.now(UTC),
        )

        # Should match
        matches = _evaluate_triggers(triggers, matching_post, is_mention=False)
        assert len(matches) == 1

        # Should not match
        matches = _evaluate_triggers(triggers, non_matching_post, is_mention=False)
        assert len(matches) == 0

    def test_engagement_threshold_trigger(self) -> None:
        """Engagement threshold trigger should match high-engagement posts."""
        from unittest.mock import MagicMock

        from kairix_agent.social.channels.base import SocialPost
        from kairix_agent.social.models import TriggerAction, TriggerType
        from kairix_agent.worker.jobs.social_explore import _evaluate_triggers

        trigger = MagicMock()
        trigger.id = str(uuid4())
        trigger.trigger_type = TriggerType.ENGAGEMENT_THRESHOLD.value
        trigger.config = {"min_likes": 100}
        trigger.cooldown_minutes = 5
        trigger.last_fired_at = None
        trigger.enabled = True
        trigger.action = TriggerAction.WAKE_AND_EVALUATE.value
        triggers = [trigger]

        high_engagement_post = SocialPost(
            external_id="at://test/post",
            author_handle="user.bsky.social",
            author_display_name="User",
            author_did="did:plc:user",
            content="Viral post",
            created_at=datetime.now(UTC),
            like_count=150,
        )

        low_engagement_post = SocialPost(
            external_id="at://test/post2",
            author_handle="user.bsky.social",
            author_display_name="User",
            author_did="did:plc:user",
            content="Regular post",
            created_at=datetime.now(UTC),
            like_count=10,
        )

        # High engagement should match
        matches = _evaluate_triggers(triggers, high_engagement_post, is_mention=False)
        assert len(matches) == 1

        # Low engagement should not match
        matches = _evaluate_triggers(triggers, low_engagement_post, is_mention=False)
        assert len(matches) == 0

    def test_cooldown_prevents_trigger_firing(self) -> None:
        """Trigger should not fire if within cooldown period."""
        from unittest.mock import MagicMock

        from kairix_agent.social.channels.base import SocialPost
        from kairix_agent.social.models import TriggerAction, TriggerType
        from kairix_agent.worker.jobs.social_explore import _evaluate_triggers

        trigger = MagicMock()
        trigger.id = str(uuid4())
        trigger.trigger_type = TriggerType.DIRECT_MENTION.value
        trigger.config = {}
        trigger.cooldown_minutes = 30
        # Fired just now (within cooldown)
        trigger.last_fired_at = datetime.now(UTC)
        trigger.enabled = True
        trigger.action = TriggerAction.WAKE_AND_EVALUATE.value
        triggers = [trigger]

        post = SocialPost(
            external_id="at://test/post",
            author_handle="user.bsky.social",
            author_display_name="User",
            author_did="did:plc:user",
            content="Test mention",
            created_at=datetime.now(UTC),
        )

        # Should not match due to cooldown
        matches = _evaluate_triggers(triggers, post, is_mention=True)
        assert len(matches) == 0
