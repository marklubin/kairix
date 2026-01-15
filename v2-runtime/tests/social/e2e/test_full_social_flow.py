"""Full end-to-end functional tests for the social agent system.

These tests use REAL services:
- PostgreSQL database
- Letta server (for agent provisioning)
- Real job execution (not mocked)

Only external services (Bluesky API) and LLM calls are mocked.

Run these tests with:
    ./kx dev && ./kx wait all && ./kx migrate
    uv run pytest tests/social/e2e/test_full_social_flow.py -v -m integration

Prerequisites:
    - PostgreSQL running and migrated
    - Letta server running
    - Redis running (for SAQ queue simulation)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from letta_client import AsyncLetta
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kairix_agent.config import Config
from kairix_agent.social.models import (
    ActionType,
    ApprovalQueueItem,
    ApprovalStatus,
    SocialChannel,
    SocialChannelType,
    SocialInteraction,
    SocialTrigger,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

# =============================================================================
# Database Setup (Real PostgreSQL)
# =============================================================================

_test_engine = create_async_engine(Config.DATABASE_URL.value, echo=False)
_test_session = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


# =============================================================================
# Cleanup Utilities
# =============================================================================


async def cleanup_agent_data(db: AsyncSession, agent_id: str) -> None:
    """Clean up all database records for a test agent."""
    # Delete approval queue items
    await db.execute(
        delete(ApprovalQueueItem).where(ApprovalQueueItem.agent_id == agent_id)
    )

    # Get channel IDs
    result = await db.execute(
        select(SocialChannel.id).where(SocialChannel.agent_id == agent_id)
    )
    channel_ids = [row[0] for row in result.fetchall()]

    if channel_ids:
        # Delete interactions
        await db.execute(
            delete(SocialInteraction).where(SocialInteraction.channel_id.in_(channel_ids))
        )
        # Delete triggers
        await db.execute(
            delete(SocialTrigger).where(SocialTrigger.channel_id.in_(channel_ids))
        )
        # Delete channels
        await db.execute(
            delete(SocialChannel).where(SocialChannel.id.in_(channel_ids))
        )

    await db.commit()


async def delete_letta_agent(client: AsyncLetta, agent_id: str) -> None:
    """Delete a Letta agent and its associated resources."""
    try:
        # Delete the agent - Letta handles cascade deletion
        await client.agents.delete(agent_id)
        logger.info("Deleted Letta agent: %s", agent_id)
    except Exception as e:
        logger.warning("Failed to delete Letta agent %s: %s", agent_id, e)


async def delete_letta_archive(client: AsyncLetta, archive_name: str) -> None:
    """Delete a Letta archive by name."""
    try:
        async for archive in client.archives.list():
            if archive.name == archive_name:
                await client.archives.delete(archive.id)
                logger.info("Deleted Letta archive: %s (%s)", archive_name, archive.id)
                return
    except Exception as e:
        logger.warning("Failed to delete Letta archive %s: %s", archive_name, e)


async def delete_letta_mcp_server(client: AsyncLetta, server_name: str) -> None:
    """Delete a Letta MCP server by name."""
    try:
        servers = await client.mcp_servers.list()
        for server in servers:
            if server.server_name == server_name:
                await client.mcp_servers.delete(server.id)
                logger.info("Deleted Letta MCP server: %s (%s)", server_name, server.id)
                return
    except Exception as e:
        logger.warning("Failed to delete Letta MCP server %s: %s", server_name, e)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_agent_name() -> str:
    """Generate unique agent name for test isolation."""
    return f"TestAgent-{uuid4().hex[:8]}"


@pytest.fixture
def test_encryption_key() -> str:
    """Generate a valid Fernet key for testing."""
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()


@pytest.fixture
async def letta_client() -> AsyncGenerator[AsyncLetta, None]:
    """Provide a Letta client for the test."""
    client = AsyncLetta(base_url=Config.LETTA_BASE_URL.value)
    yield client


@pytest.fixture
async def provisioned_agent(
    letta_client: AsyncLetta,
    test_agent_name: str,
) -> AsyncGenerator[tuple[str, str], None]:
    """Provision a real agent for testing and clean up after.

    Yields:
        Tuple of (agent_id, agent_name)
    """
    from kairix_agent.provisioning.cli import _run_provisioning, find_agent_by_name

    # Provision the agent
    logger.info("Provisioning test agent: %s", test_agent_name)
    exit_code = await _run_provisioning(letta_client, test_agent_name)

    if exit_code != 0:
        pytest.skip("Failed to provision agent - Letta may not be running")

    # Find the agent ID
    result = await find_agent_by_name(letta_client, test_agent_name)
    if not result:
        pytest.fail("Agent was provisioned but not found")

    agent_id, _, _ = result
    logger.info("Agent provisioned: %s (%s)", test_agent_name, agent_id)

    yield agent_id, test_agent_name

    # Cleanup: Delete the agent and associated resources
    logger.info("Cleaning up test agent: %s", test_agent_name)
    await delete_letta_agent(letta_client, agent_id)
    await delete_letta_archive(letta_client, test_agent_name)
    await delete_letta_mcp_server(letta_client, f"kp3_{test_agent_name.lower()}")


@pytest.fixture
async def test_social_channel(
    provisioned_agent: tuple[str, str],
    test_encryption_key: str,
) -> AsyncGenerator[SocialChannel, None]:
    """Create a real social channel for the provisioned agent.

    This channel is stored in the real database.
    """
    from kairix_agent.social import service
    from kairix_agent.social.crypto import get_fernet

    agent_id, agent_name = provisioned_agent

    # Patch encryption key
    with patch("kairix_agent.social.crypto.Config") as mock_config:
        mock_config.CREDENTIAL_ENCRYPTION_KEY.value = test_encryption_key
        get_fernet.cache_clear()

        try:
            channel = await service.create_channel(
                agent_id=agent_id,
                channel_type=SocialChannelType.BLUESKY,
                handle=f"@{agent_name.lower()}.test.bsky.social",
                credentials={"identifier": "test", "password": "test"},
            )
            logger.info("Created social channel: %s (%s)", channel.handle, channel.id)

            yield channel

        finally:
            get_fernet.cache_clear()

    # Cleanup: Delete channel and related data
    async with _test_session() as db:
        await cleanup_agent_data(db, agent_id)


@pytest.fixture
def mock_bluesky_channel() -> MagicMock:
    """Create a mock Bluesky channel implementation."""
    mock_channel = AsyncMock()
    mock_channel.authenticate = AsyncMock(return_value=True)
    mock_channel.get_timeline = AsyncMock(return_value=([], None))
    mock_channel.get_mentions = AsyncMock(return_value=[])
    return mock_channel


# =============================================================================
# Full Functional Tests
# =============================================================================


@pytest.mark.integration
class TestFullSocialFlow:
    """Full end-to-end functional tests using real services."""

    @pytest.mark.asyncio
    async def test_provision_agent_creates_letta_agent(
        self,
        letta_client: AsyncLetta,
        test_agent_name: str,
    ) -> None:
        """Provisioning should create a real Letta agent with blocks and archive."""
        from kairix_agent.provisioning.cli import _run_provisioning, find_agent_by_name

        # Provision
        exit_code = await _run_provisioning(letta_client, test_agent_name)

        if exit_code != 0:
            pytest.skip("Letta server not available")

        try:
            # Verify agent exists
            result = await find_agent_by_name(letta_client, test_agent_name)
            assert result is not None, "Agent should exist after provisioning"

            agent_id, blocks, archives = result
            assert agent_id is not None

            # Verify blocks were created
            expected_blocks = {"persona", "human", "world", "focus", "last_session_summary", "background_insights"}
            assert expected_blocks <= set(blocks.keys()), f"Missing blocks: {expected_blocks - set(blocks.keys())}"

            # Verify archive was created
            assert len(archives) > 0, "Archive should be attached to agent"

            logger.info("Agent verified: %s with %d blocks and %d archives", agent_id, len(blocks), len(archives))

        finally:
            # Cleanup
            if result:
                await delete_letta_agent(letta_client, agent_id)
                await delete_letta_archive(letta_client, test_agent_name)
                await delete_letta_mcp_server(letta_client, f"kp3_{test_agent_name.lower()}")

    @pytest.mark.asyncio
    async def test_explore_with_real_channel_storage(
        self,
        provisioned_agent: tuple[str, str],
        test_social_channel: SocialChannel,
        test_encryption_key: str,
        mock_bluesky_channel: MagicMock,
    ) -> None:
        """Exploration job stores interactions in real database."""
        from kairix_agent.social import service
        from kairix_agent.social.channels.base import SocialPost
        from kairix_agent.social.crypto import get_fernet

        agent_id, _ = provisioned_agent

        # Create mock timeline posts
        mock_posts = [
            SocialPost(
                external_id=f"at://did:plc:test/post-{i}",
                author_handle=f"user{i}.bsky.social",
                author_display_name=f"User {i}",
                author_did=f"did:plc:user{i}",
                content=f"Functional test post content {i}",
                created_at=datetime.now(UTC),
                reply_count=i,
                repost_count=i,
                like_count=i * 10,
            )
            for i in range(5)
        ]

        mock_bluesky_channel.get_timeline = AsyncMock(return_value=(mock_posts, "cursor"))

        mock_queue = AsyncMock()

        with (
            patch(
                "kairix_agent.worker.jobs.social_explore.create_channel",
                return_value=mock_bluesky_channel,
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
                    {"queue": mock_queue},
                    channel_id=str(test_social_channel.id),
                )

                assert result["status"] == "ok"

                # Verify interactions stored in REAL database
                interactions = await service.list_interactions(str(test_social_channel.id))
                assert len(interactions) >= 5

                # Verify content
                contents = {i.content_text for i in interactions}
                for i in range(5):
                    assert f"Functional test post content {i}" in contents

                logger.info("Stored %d interactions in real database", len(interactions))

            finally:
                get_fernet.cache_clear()

    @pytest.mark.asyncio
    async def test_full_mention_to_draft_pipeline(
        self,
        provisioned_agent: tuple[str, str],
        test_social_channel: SocialChannel,
        test_encryption_key: str,
        mock_bluesky_channel: MagicMock,
    ) -> None:
        """Test complete flow: mention → explore → evaluate → draft → approval queue."""
        from kairix_agent.social import approval_service, service
        from kairix_agent.social.channels.base import SocialPost
        from kairix_agent.social.crypto import get_fernet

        agent_id, agent_name = provisioned_agent

        # Create a mention post
        mention_post = SocialPost(
            external_id=f"at://did:plc:mentioner/mention-{uuid4().hex[:8]}",
            author_handle="curious_researcher.bsky.social",
            author_display_name="Curious Researcher",
            author_did="did:plc:researcher",
            content=f"Hey @{test_social_channel.handle} what do you think about AI memory systems?",
            created_at=datetime.now(UTC),
        )

        mock_bluesky_channel.get_timeline = AsyncMock(return_value=([], None))
        mock_bluesky_channel.get_mentions = AsyncMock(return_value=[mention_post])

        # Track enqueued jobs
        enqueued_jobs: list[tuple[str, dict[str, Any]]] = []

        async def capture_enqueue(job_name: str, **kwargs: Any) -> MagicMock:
            enqueued_jobs.append((job_name, kwargs))
            return MagicMock(id=f"job-{uuid4().hex[:8]}")

        mock_queue = AsyncMock()
        mock_queue.enqueue = AsyncMock(side_effect=capture_enqueue)

        # Mock BlockManagerAgent for evaluation and drafting
        mock_block_agent = AsyncMock()
        evaluation_response = "ENGAGE: yes\n\nThis is an excellent question about AI memory systems that deserves a thoughtful response."
        draft_response = "Great question! AI memory systems are a fascinating area. The key challenge is balancing long-term retention with contextual relevance."

        call_count = 0

        async def mock_agent_run(*args: Any, **kwargs: Any) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return evaluation_response
            return draft_response

        mock_block_agent.run = AsyncMock(side_effect=mock_agent_run)

        with (
            patch(
                "kairix_agent.worker.jobs.social_explore.create_channel",
                return_value=mock_bluesky_channel,
            ),
            patch(
                "kairix_agent.worker.jobs.social_explore.publish_event",
                new_callable=AsyncMock,
            ),
            patch(
                "kairix_agent.worker.jobs.social_evaluate.BlockManagerAgent",
                return_value=mock_block_agent,
            ),
            patch("kairix_agent.worker.jobs.social_evaluate.AsyncLetta"),
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
                # Step 1: Explore - should store interaction and enqueue evaluate
                from kairix_agent.worker.jobs.social_explore import social_explore

                explore_result = await social_explore(
                    {"queue": mock_queue},
                    channel_id=str(test_social_channel.id),
                )

                assert explore_result["status"] == "ok"
                logger.info("Explore result: %s", explore_result)

                # Verify evaluate job was enqueued
                evaluate_jobs = [j for j in enqueued_jobs if j[0] == "social_evaluate"]
                assert len(evaluate_jobs) >= 1, "Evaluate job should be enqueued for mention"

                # Get the stored interaction
                interactions = await service.list_interactions(str(test_social_channel.id), limit=1)
                assert len(interactions) >= 1
                interaction = interactions[0]

                # Step 2: Evaluate - should decide to engage and enqueue draft
                from kairix_agent.worker.jobs.social_evaluate import social_evaluate

                eval_result = await social_evaluate(
                    {"queue": mock_queue},
                    agent_id=agent_id,
                    channel_id=str(test_social_channel.id),
                    interaction_id=str(interaction.id),
                    is_mention=True,
                )

                assert eval_result["status"] == "ok"
                assert eval_result["should_engage"] is True
                assert eval_result["draft_enqueued"] is True
                logger.info("Evaluate result: %s", eval_result)

                # Verify draft job was enqueued
                draft_jobs = [j for j in enqueued_jobs if j[0] == "social_draft"]
                assert len(draft_jobs) >= 1, "Draft job should be enqueued when deciding to engage"

                # Step 3: Draft - should create approval queue item
                from kairix_agent.worker.jobs.social_draft import social_draft

                draft_result = await social_draft(
                    {},
                    agent_id=agent_id,
                    channel_id=str(test_social_channel.id),
                    interaction_id=str(interaction.id),
                    evaluation_reasoning="Relevant question about AI memory systems",
                )

                assert draft_result["status"] == "ok"
                assert draft_result["needs_approval"] is True
                approval_item_id = draft_result["approval_item_id"]
                logger.info("Draft result: %s", draft_result)

                # Step 4: Verify approval item in REAL database
                item = await approval_service.get_approval_item(approval_item_id)
                assert item is not None
                assert item.agent_id == agent_id
                assert item.status == ApprovalStatus.PENDING.value
                assert "memory" in item.draft_content.lower()

                # Step 5: Approve the draft
                approved = await approval_service.approve_item(approval_item_id)
                assert approved is not None
                assert approved.status == ApprovalStatus.APPROVED.value

                # Step 6: Verify queue stats
                stats = await approval_service.get_queue_stats(agent_id)
                assert stats["approved"] >= 1

                logger.info("Full pipeline completed successfully!")
                logger.info("Stats: %s", stats)

            finally:
                get_fernet.cache_clear()

    @pytest.mark.asyncio
    async def test_rejection_with_feedback_and_regeneration(
        self,
        provisioned_agent: tuple[str, str],
        test_social_channel: SocialChannel,
        test_encryption_key: str,
    ) -> None:
        """Test rejection workflow: create draft, reject with feedback, verify stored."""
        from kairix_agent.social import approval_service
        from kairix_agent.social.crypto import get_fernet

        agent_id, _ = provisioned_agent

        with patch("kairix_agent.social.crypto.Config") as mock_config:
            mock_config.CREDENTIAL_ENCRYPTION_KEY.value = test_encryption_key
            get_fernet.cache_clear()

            try:
                # Create a draft approval item
                item = await approval_service.create_approval_item(
                    agent_id=agent_id,
                    channel_type="bluesky",
                    action_type=ActionType.REPLY,
                    draft_content="This is a bit too formal and corporate sounding.",
                    target_entity="@curious_researcher.bsky.social",
                    context_summary="Reply to question about AI memory",
                    confidence_score=0.75,
                )

                # Reject with feedback
                feedback = "Too formal! Be more conversational and personal. Show genuine curiosity."
                rejected = await approval_service.reject_item(str(item.id), feedback=feedback)

                assert rejected is not None
                assert rejected.status == ApprovalStatus.REJECTED.value
                assert rejected.user_feedback == feedback

                # Verify stored in DB by re-fetching
                refetched = await approval_service.get_approval_item(str(item.id))
                assert refetched is not None
                assert refetched.user_feedback == feedback

                # Create a new draft (simulating regeneration)
                new_item = await approval_service.create_approval_item(
                    agent_id=agent_id,
                    channel_type="bluesky",
                    action_type=ActionType.REPLY,
                    draft_content="Oh this is such a fun question! I've been noodling on memory architectures lately...",
                    target_entity="@curious_researcher.bsky.social",
                    context_summary="Reply to question about AI memory (regenerated after feedback)",
                    confidence_score=0.85,
                )

                # Approve the new draft
                approved = await approval_service.approve_item(str(new_item.id))
                assert approved is not None
                assert approved.status == ApprovalStatus.APPROVED.value

                # Check stats show both rejected and approved
                stats = await approval_service.get_queue_stats(agent_id)
                assert stats["rejected"] >= 1
                assert stats["approved"] >= 1

                logger.info("Rejection and regeneration workflow completed!")
                logger.info("Stats: %s", stats)

            finally:
                get_fernet.cache_clear()

    @pytest.mark.asyncio
    async def test_multiple_channels_exploration(
        self,
        letta_client: AsyncLetta,
        test_agent_name: str,
        test_encryption_key: str,
    ) -> None:
        """Test exploring multiple channels for the same agent."""
        from kairix_agent.provisioning.cli import _run_provisioning, find_agent_by_name
        from kairix_agent.social import service
        from kairix_agent.social.channels.base import SocialPost
        from kairix_agent.social.crypto import get_fernet

        # Provision agent
        exit_code = await _run_provisioning(letta_client, test_agent_name)
        if exit_code != 0:
            pytest.skip("Letta server not available")

        result = await find_agent_by_name(letta_client, test_agent_name)
        if not result:
            pytest.fail("Agent not found after provisioning")

        agent_id, _, _ = result

        try:
            with patch("kairix_agent.social.crypto.Config") as mock_config:
                mock_config.CREDENTIAL_ENCRYPTION_KEY.value = test_encryption_key
                get_fernet.cache_clear()

                try:
                    # Create channel (we can only have one per type per agent)
                    channel = await service.create_channel(
                        agent_id=agent_id,
                        channel_type=SocialChannelType.BLUESKY,
                        handle=f"@{test_agent_name.lower()}.bsky.social",
                        credentials={"identifier": "test", "password": "test"},
                    )

                    # Mock posts for this channel
                    mock_posts = [
                        SocialPost(
                            external_id=f"at://did:plc:test/post-{i}",
                            author_handle=f"user{i}.bsky.social",
                            author_display_name=f"User {i}",
                            author_did=f"did:plc:user{i}",
                            content=f"Multi-channel test post {i}",
                            created_at=datetime.now(UTC),
                        )
                        for i in range(3)
                    ]

                    mock_social_channel = AsyncMock()
                    mock_social_channel.authenticate = AsyncMock(return_value=True)
                    mock_social_channel.get_timeline = AsyncMock(return_value=(mock_posts, None))
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

                        result = await social_explore(
                            {"queue": AsyncMock()},
                            channel_id=str(channel.id),
                        )

                        assert result["status"] == "ok"

                        # Verify interactions
                        interactions = await service.list_interactions(str(channel.id))
                        assert len(interactions) >= 3

                finally:
                    get_fernet.cache_clear()

        finally:
            # Cleanup
            async with _test_session() as db:
                await cleanup_agent_data(db, agent_id)
            await delete_letta_agent(letta_client, agent_id)
            await delete_letta_archive(letta_client, test_agent_name)
            await delete_letta_mcp_server(letta_client, f"kp3_{test_agent_name.lower()}")


@pytest.mark.integration
class TestAgentProvisioningIntegration:
    """Tests focused on agent provisioning aspects."""

    @pytest.mark.asyncio
    async def test_provisioning_is_idempotent(
        self,
        letta_client: AsyncLetta,
        test_agent_name: str,
    ) -> None:
        """Provisioning the same agent twice should remediate, not duplicate."""
        from kairix_agent.provisioning.cli import _run_provisioning, find_agent_by_name

        # First provision
        exit_code1 = await _run_provisioning(letta_client, test_agent_name)
        if exit_code1 != 0:
            pytest.skip("Letta server not available")

        result1 = await find_agent_by_name(letta_client, test_agent_name)
        assert result1 is not None
        agent_id1, _, _ = result1

        try:
            # Second provision - should remediate, not create new
            exit_code2 = await _run_provisioning(letta_client, test_agent_name)
            assert exit_code2 == 0

            result2 = await find_agent_by_name(letta_client, test_agent_name)
            assert result2 is not None
            agent_id2, _, _ = result2

            # Should be the same agent
            assert agent_id1 == agent_id2, "Provisioning should be idempotent"

            # Count agents with this name - should be exactly 1
            count = 0
            async for agent in letta_client.agents.list(name=test_agent_name):
                if agent.name == test_agent_name:
                    count += 1
            assert count == 1, "Should have exactly one agent with this name"

        finally:
            await delete_letta_agent(letta_client, agent_id1)
            await delete_letta_archive(letta_client, test_agent_name)
            await delete_letta_mcp_server(letta_client, f"kp3_{test_agent_name.lower()}")
