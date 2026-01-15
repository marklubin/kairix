"""Shared fixtures for social agent tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from kairix_agent.social.channels.base import SocialPost
    from kairix_agent.social.models import SocialChannel


# =============================================================================
# Agent Fixtures
# =============================================================================


@pytest.fixture
def ephemeral_agent_id() -> str:
    """Generate unique agent ID for test isolation."""
    return f"test-agent-{uuid4().hex[:8]}"


# =============================================================================
# Mock Data Factories
# =============================================================================


def make_mock_social_post(
    post_id: str | None = None,
    author_handle: str = "testuser.bsky.social",
    author_did: str = "did:plc:testuser",
    content: str = "Test post content",
    like_count: int = 10,
    is_reply: bool = False,
) -> SocialPost:
    """Create a mock SocialPost for testing."""
    from kairix_agent.social.channels.base import SocialPost as SocialPostClass

    if post_id is None:
        post_id = f"at://did:plc:test/{uuid4().hex[:8]}"

    return SocialPostClass(
        external_id=post_id,
        author_handle=author_handle,
        author_display_name=author_handle.split(".")[0].title(),
        author_did=author_did,
        content=content,
        created_at=datetime.now(UTC),
        reply_count=5,
        repost_count=2,
        like_count=like_count,
        parent_id=f"at://did:plc:parent/{uuid4().hex[:8]}" if is_reply else None,
        root_id=f"at://did:plc:root/{uuid4().hex[:8]}" if is_reply else None,
        has_media=False,
    )


def make_mock_timeline_response(
    num_posts: int = 5,
    cursor: str | None = "next-cursor",
) -> tuple[list[SocialPost], str | None]:
    """Create mock timeline response."""
    posts = [
        make_mock_social_post(
            post_id=f"at://did:plc:test/post-{i}",
            content=f"Timeline post {i}",
            like_count=i * 10,
        )
        for i in range(num_posts)
    ]
    return posts, cursor


def make_mock_mention_post(
    mentioned_handle: str = "agent.bsky.social",
) -> SocialPost:
    """Create a mock mention/reply post."""
    return make_mock_social_post(
        content=f"Hey @{mentioned_handle} what do you think about this?",
        author_handle="mentioner.bsky.social",
        author_did="did:plc:mentioner",
        is_reply=True,
    )


# =============================================================================
# Bluesky Client Mocks
# =============================================================================


@pytest.fixture
def mock_bluesky_client() -> MagicMock:
    """Mock atproto.AsyncClient for Bluesky operations."""
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


def make_mock_feed_item(
    post_id: str = "post-1",
    author_handle: str = "testuser.bsky.social",
    author_did: str = "did:plc:testuser",
    content: str = "Test post content",
    like_count: int = 10,
) -> MagicMock:
    """Create mock atproto feed item structure."""
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


def make_mock_notification(
    reason: str = "mention",
    author_handle: str = "mentioner.bsky.social",
    author_did: str = "did:plc:mentioner",
    content: str = "Hey @agent what do you think?",
) -> MagicMock:
    """Create mock notification structure."""
    notif = MagicMock()
    notif.reason = reason
    notif.uri = f"at://{author_did}/post-{uuid4().hex[:8]}"
    notif.author = MagicMock()
    notif.author.handle = author_handle
    notif.author.did = author_did
    notif.author.display_name = author_handle.split(".")[0].title()
    notif.record = MagicMock()
    notif.record.text = content
    notif.indexed_at = datetime.now(UTC).isoformat() + "Z"
    notif.is_read = False
    return notif


# =============================================================================
# BlockManagerAgent Mocks
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
# Database Session Mocks
# =============================================================================


def make_mock_db_session() -> AsyncMock:
    """Create a mock async database session."""
    mock_session = AsyncMock()

    # Context manager support
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    # Common operations
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.delete = AsyncMock()

    return mock_session


def make_mock_session_factory(session: AsyncMock) -> MagicMock:
    """Create a mock sessionmaker that returns the given session."""
    factory = MagicMock()
    factory.return_value = session
    return factory


# =============================================================================
# SAQ Queue Mocks
# =============================================================================


@pytest.fixture
def mock_saq_queue() -> AsyncMock:
    """Create a mock SAQ queue for job enqueueing."""
    queue = AsyncMock()
    queue.enqueue = AsyncMock(return_value=MagicMock(id="job-123"))
    return queue


@pytest.fixture
def mock_saq_context(mock_saq_queue: AsyncMock) -> dict[str, Any]:
    """Create a mock SAQ job context."""
    return {"queue": mock_saq_queue}


# =============================================================================
# Encryption Key Fixtures
# =============================================================================


@pytest.fixture
def test_encryption_key() -> str:
    """Generate a valid Fernet key for testing."""
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()


# =============================================================================
# Event Publishing Mocks
# =============================================================================


@pytest.fixture
def mock_publish_event() -> AsyncMock:
    """Mock for the publish_event function."""
    return AsyncMock()


# =============================================================================
# Letta Client Mocks
# =============================================================================


@pytest.fixture
def mock_letta_client() -> AsyncMock:
    """Create a mock AsyncLetta client."""
    client = AsyncMock()
    return client
