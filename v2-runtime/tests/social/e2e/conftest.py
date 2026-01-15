"""E2E test fixtures using real database connections.

These fixtures connect to the real PostgreSQL database when services are running.
Start services with: ./kx dev && ./kx wait postgres && ./kx migrate

Tests using these fixtures should be marked with @pytest.mark.integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kairix_agent.config import Config
from kairix_agent.social.models import (
    ApprovalQueueItem,
    SocialChannel,
    SocialInteraction,
    SocialTrigger,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# =============================================================================
# Real Database Engine (connects to local postgres via ./kx dev)
# =============================================================================

# Real database engine for integration tests
_test_engine = create_async_engine(Config.DATABASE_URL.value, echo=False)
_test_session = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Real database session for integration tests.

    Use this for direct database operations in tests.
    Rolls back any uncommitted changes after the test.
    """
    async with _test_session() as session:
        yield session
        # Rollback any uncommitted changes
        await session.rollback()


# =============================================================================
# Test Data Cleanup
# =============================================================================


async def cleanup_test_agent_data(db: AsyncSession, agent_id: str) -> None:
    """Clean up all test data for a specific agent.

    Args:
        db: Database session.
        agent_id: Agent ID to clean up.
    """
    # Delete in order to respect foreign key constraints
    # 1. Approval queue items (references interactions)
    await db.execute(
        delete(ApprovalQueueItem).where(ApprovalQueueItem.agent_id == agent_id)
    )

    # 2. Get channel IDs for this agent
    from sqlalchemy import select

    channel_result = await db.execute(
        select(SocialChannel.id).where(SocialChannel.agent_id == agent_id)
    )
    channel_ids = [row[0] for row in channel_result.fetchall()]

    if channel_ids:
        # 3. Delete interactions (references channels)
        await db.execute(
            delete(SocialInteraction).where(SocialInteraction.channel_id.in_(channel_ids))
        )
        # 4. Delete triggers (references channels)
        await db.execute(
            delete(SocialTrigger).where(SocialTrigger.channel_id.in_(channel_ids))
        )
        # 5. Delete channels
        await db.execute(
            delete(SocialChannel).where(SocialChannel.id.in_(channel_ids))
        )

    await db.commit()


# =============================================================================
# Agent Fixtures
# =============================================================================


@pytest.fixture
def ephemeral_agent_id() -> str:
    """Generate unique agent ID for test isolation."""
    return f"test-agent-{uuid4().hex[:8]}"


@pytest.fixture
async def cleanup_agent(db_session: AsyncSession, ephemeral_agent_id: str) -> AsyncGenerator[str, None]:
    """Fixture that provides agent ID and cleans up after test.

    Use this instead of ephemeral_agent_id when you want automatic cleanup.
    """
    yield ephemeral_agent_id
    await cleanup_test_agent_data(db_session, ephemeral_agent_id)


# =============================================================================
# Real Channel Fixtures
# =============================================================================


@pytest.fixture
async def test_channel(
    cleanup_agent: str,
    test_encryption_key: str,
) -> AsyncGenerator[SocialChannel, None]:
    """Create a real channel in the database, cleanup after test.

    This creates an actual database record. The test_encryption_key fixture
    patches the Config to use a test key for credential encryption.
    """
    from unittest.mock import patch

    from kairix_agent.social import service
    from kairix_agent.social.crypto import get_fernet
    from kairix_agent.social.models import SocialChannelType

    # Patch the encryption key for this test
    with patch("kairix_agent.social.crypto.Config") as mock_config:
        mock_config.CREDENTIAL_ENCRYPTION_KEY.value = test_encryption_key
        get_fernet.cache_clear()

        try:
            channel = await service.create_channel(
                agent_id=cleanup_agent,
                channel_type=SocialChannelType.BLUESKY,
                handle=f"@test-{uuid4().hex[:8]}.bsky.social",
                credentials={"identifier": "test", "password": "test"},
            )
            yield channel
        finally:
            get_fernet.cache_clear()


# =============================================================================
# Encryption Key Fixture
# =============================================================================


@pytest.fixture
def test_encryption_key() -> str:
    """Generate a valid Fernet key for testing."""
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()


# =============================================================================
# Bluesky Client Mocks (external service - always mocked)
# =============================================================================


@pytest.fixture
def mock_bluesky_client() -> MagicMock:
    """Mock atproto.AsyncClient for Bluesky operations.

    External services are always mocked even in integration tests.
    """
    from datetime import UTC, datetime

    mock = MagicMock()

    # Auth
    mock.login = AsyncMock(return_value=None)
    mock.me = MagicMock()
    mock.me.did = "did:plc:testagent"
    mock.me.handle = "testagent.bsky.social"

    # Timeline - returns raw atproto response structure
    timeline_response = MagicMock()
    timeline_response.cursor = "next-cursor"
    timeline_response.feed = []  # Will be populated per test
    mock.get_timeline = AsyncMock(return_value=timeline_response)

    # Notifications
    notif_response = MagicMock()
    notif_response.notifications = []
    mock.app = MagicMock()
    mock.app.bsky = MagicMock()
    mock.app.bsky.notification = MagicMock()
    mock.app.bsky.notification.list_notifications = AsyncMock(return_value=notif_response)

    # Post operations
    post_result = MagicMock()
    post_result.uri = f"at://did:plc:testagent/{uuid4().hex[:8]}"
    mock.send_post = AsyncMock(return_value=post_result)
    mock.get_posts = AsyncMock(return_value=MagicMock(posts=[]))
    mock.get_post_thread = AsyncMock(return_value=MagicMock(thread=MagicMock(post=None)))

    # Actions
    mock.like = AsyncMock(return_value=None)
    mock.unlike = AsyncMock(return_value=None)
    mock.repost = AsyncMock(return_value=None)
    mock.unrepost = AsyncMock(return_value=None)
    mock.follow = AsyncMock(return_value=None)
    mock.unfollow = AsyncMock(return_value=None)
    mock.mute = AsyncMock(return_value=None)
    mock.unmute = AsyncMock(return_value=None)

    # Profile
    profile = MagicMock()
    profile.did = "did:plc:testagent"
    profile.handle = "testagent.bsky.social"
    profile.display_name = "Test Agent"
    profile.description = "A test agent"
    profile.followers_count = 100
    profile.follows_count = 50
    profile.posts_count = 25
    profile.avatar = None
    profile.labels = []
    mock.get_profile = AsyncMock(return_value=profile)

    # Search
    mock.app.bsky.feed = MagicMock()
    mock.app.bsky.feed.search_posts = AsyncMock(return_value=MagicMock(posts=[]))

    # Time helper
    mock.get_current_time_iso = MagicMock(return_value=datetime.now(UTC).isoformat())

    return mock


# =============================================================================
# Mock Factories for Feed Data
# =============================================================================


def make_mock_feed_item(
    post_id: str = "post-1",
    author_handle: str = "testuser.bsky.social",
    author_did: str = "did:plc:testuser",
    content: str = "Test post content",
    like_count: int = 10,
) -> MagicMock:
    """Create mock atproto feed item structure."""
    from datetime import UTC, datetime

    item = MagicMock()
    item.post = MagicMock()
    item.post.uri = f"at://{author_did}/{post_id}"
    item.post.cid = f"cid-{post_id}"
    item.post.author = MagicMock()
    item.post.author.handle = author_handle
    item.post.author.did = author_did
    item.post.author.display_name = author_handle.split(".")[0].title()
    item.post.record = MagicMock()
    item.post.record.text = content
    item.post.record.reply = None
    item.post.record.embed = None
    item.post.indexed_at = datetime.now(UTC).isoformat() + "Z"
    item.post.reply_count = 5
    item.post.repost_count = 2
    item.post.like_count = like_count
    item.post.labels = []
    return item


def make_mock_timeline_response(
    num_posts: int = 5,
    offset: int = 0,
) -> MagicMock:
    """Create mock timeline response with multiple posts."""
    mock_response = MagicMock()
    mock_response.cursor = f"cursor-{offset}"
    mock_response.feed = [
        make_mock_feed_item(
            post_id=f"post-{offset + i}",
            content=f"Post content {offset + i}",
            like_count=(offset + i) * 10,
        )
        for i in range(num_posts)
    ]
    return mock_response


def make_mock_mention_notification(
    agent_handle: str,
    author_handle: str = "mentioner.bsky.social",
    author_did: str = "did:plc:mentioner",
    content: str | None = None,
) -> MagicMock:
    """Create mock notification with mention."""
    from datetime import UTC, datetime

    if content is None:
        content = f"Hey @{agent_handle} what do you think?"

    mock_response = MagicMock()
    mock_response.cursor = "mention-cursor"
    notif = MagicMock()
    notif.reason = "mention"
    notif.uri = f"at://{author_did}/mention-post-{uuid4().hex[:8]}"
    notif.cid = f"cid-mention-{uuid4().hex[:8]}"
    notif.author = MagicMock()
    notif.author.handle = author_handle
    notif.author.did = author_did
    notif.author.display_name = author_handle.split(".")[0].title()
    notif.record = MagicMock()
    notif.record.text = content
    notif.record.reply = None
    notif.indexed_at = datetime.now(UTC).isoformat() + "Z"
    notif.is_read = False
    mock_response.notifications = [notif]
    return mock_response


# =============================================================================
# BlockManagerAgent Mocks (LLM - always mocked)
# =============================================================================


@pytest.fixture
def mock_block_manager_responses() -> dict[str, str]:
    """Configure mock responses for BlockManagerAgent."""
    return {
        "social_evaluate": "ENGAGE: yes\n\nThis post is relevant and worth responding to.",
        "social_draft": "Great point! I've been thinking about this topic too. The implications are fascinating.",
        "social_episode_summarize": "Had a conversation about AI memory systems with @researcher",
        "social_reflect": "Learned that @researcher values technical depth over marketing speak.",
    }


def setup_block_manager_mock(mock_class: MagicMock, response: str) -> MagicMock:
    """Configure BlockManagerAgent mock to return specified response."""
    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(return_value=response)
    mock_agent.register_tool_handler = MagicMock()
    mock_class.return_value = mock_agent
    return mock_agent


# =============================================================================
# SAQ Queue Mock (job queue - always mocked in e2e)
# =============================================================================


@pytest.fixture
def mock_saq_queue() -> AsyncMock:
    """Create a mock SAQ queue for job enqueueing."""
    queue = AsyncMock()
    queue.enqueue = AsyncMock(return_value=MagicMock(id=f"job-{uuid4().hex[:8]}"))
    return queue


@pytest.fixture
def mock_saq_context(mock_saq_queue: AsyncMock) -> dict[str, Any]:
    """Create a mock SAQ job context."""
    return {"queue": mock_saq_queue}


# =============================================================================
# Event Publishing Mock (always mocked)
# =============================================================================


@pytest.fixture
def mock_publish_event() -> AsyncMock:
    """Mock for the publish_event function."""
    return AsyncMock()
