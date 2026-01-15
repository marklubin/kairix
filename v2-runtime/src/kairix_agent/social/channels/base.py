"""Abstract base class for social channel implementations.

Defines the interface that all social platform adapters must implement.
This enables consistent behavior across Bluesky, Mastodon, X, and future platforms.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SocialUser:
    """Normalized representation of a social platform user."""

    handle: str  # @user.bsky.social
    display_name: str
    did: str | None = None  # Decentralized identifier (Bluesky)
    bio: str | None = None
    follower_count: int = 0
    following_count: int = 0
    avatar_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SocialPost:
    """Normalized representation of a social post."""

    external_id: str  # Platform-specific post ID
    author_handle: str
    author_display_name: str
    author_did: str | None  # Stable identifier for entity tracking
    content: str
    created_at: datetime

    # Engagement metrics
    reply_count: int = 0
    repost_count: int = 0
    like_count: int = 0

    # Thread context
    parent_id: str | None = None  # If this is a reply
    root_id: str | None = None  # Thread root
    quote_id: str | None = None  # If this quotes another post

    # Media and embeds
    has_media: bool = False
    has_link: bool = False
    embed_url: str | None = None

    # Platform-specific data
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PostDraft:
    """Draft post to be submitted to a platform."""

    content: str
    reply_to_id: str | None = None  # Post ID to reply to
    quote_id: str | None = None  # Post ID to quote
    # Future: media attachments, link cards, etc.


@dataclass
class PostResult:
    """Result of posting to a platform."""

    success: bool
    external_id: str | None = None  # ID of created post if successful
    error: str | None = None
    error_code: str | None = None


@dataclass
class ActionResult:
    """Result of a non-posting action (like, follow, etc.)."""

    success: bool
    error: str | None = None
    error_code: str | None = None


class AbstractSocialChannel(ABC):
    """Abstract base class for social media channel implementations.

    Implementations must handle:
    - Authentication and session management
    - Timeline and mention fetching
    - Posting, replying, quoting
    - Social actions (like, follow, block, etc.)
    - User profile lookups
    - Search functionality
    """

    # ==========================================================================
    # Authentication
    # ==========================================================================

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the platform.

        Returns:
            True if authentication successful, False otherwise
        """
        ...

    @abstractmethod
    async def is_authenticated(self) -> bool:
        """Check if currently authenticated.

        Returns:
            True if session is valid
        """
        ...

    # ==========================================================================
    # Reading Content
    # ==========================================================================

    @abstractmethod
    async def get_timeline(
        self,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[SocialPost], str | None]:
        """Fetch posts from home timeline.

        Args:
            limit: Maximum posts to return
            cursor: Pagination cursor from previous call

        Returns:
            Tuple of (posts, next_cursor) where next_cursor is None if no more
        """
        ...

    @abstractmethod
    async def get_mentions(
        self,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[SocialPost]:
        """Fetch mentions/notifications for this account.

        Args:
            since: Only return mentions after this time
            limit: Maximum mentions to return

        Returns:
            List of posts mentioning or replying to this account
        """
        ...

    @abstractmethod
    async def get_post(self, post_id: str) -> SocialPost | None:
        """Fetch a specific post by ID.

        Args:
            post_id: Platform-specific post identifier

        Returns:
            Post if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_thread(self, post_id: str) -> list[SocialPost]:
        """Fetch the full thread context for a post.

        Args:
            post_id: Any post in the thread

        Returns:
            All posts in the thread, ordered chronologically
        """
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[SocialPost]:
        """Search posts on the platform.

        Args:
            query: Search query string
            limit: Maximum results to return

        Returns:
            List of matching posts
        """
        ...

    # ==========================================================================
    # Creating Content
    # ==========================================================================

    @abstractmethod
    async def post(self, draft: PostDraft) -> PostResult:
        """Submit a new post or reply.

        Args:
            draft: Post content and optional reply/quote context

        Returns:
            Result with success status and post ID if successful
        """
        ...

    # ==========================================================================
    # Social Actions
    # ==========================================================================

    @abstractmethod
    async def like(self, post_id: str) -> ActionResult:
        """Like/favorite a post.

        Args:
            post_id: Post to like

        Returns:
            Result with success status
        """
        ...

    @abstractmethod
    async def unlike(self, post_id: str) -> ActionResult:
        """Remove like from a post.

        Args:
            post_id: Post to unlike

        Returns:
            Result with success status
        """
        ...

    @abstractmethod
    async def repost(self, post_id: str) -> ActionResult:
        """Repost/retweet a post.

        Args:
            post_id: Post to repost

        Returns:
            Result with success status
        """
        ...

    @abstractmethod
    async def unrepost(self, post_id: str) -> ActionResult:
        """Remove repost.

        Args:
            post_id: Post to un-repost

        Returns:
            Result with success status
        """
        ...

    @abstractmethod
    async def follow(self, user_handle: str) -> ActionResult:
        """Follow a user.

        Args:
            user_handle: Handle to follow

        Returns:
            Result with success status
        """
        ...

    @abstractmethod
    async def unfollow(self, user_handle: str) -> ActionResult:
        """Unfollow a user.

        Args:
            user_handle: Handle to unfollow

        Returns:
            Result with success status
        """
        ...

    @abstractmethod
    async def block(self, user_handle: str) -> ActionResult:
        """Block a user.

        Args:
            user_handle: Handle to block

        Returns:
            Result with success status
        """
        ...

    @abstractmethod
    async def unblock(self, user_handle: str) -> ActionResult:
        """Unblock a user.

        Args:
            user_handle: Handle to unblock

        Returns:
            Result with success status
        """
        ...

    @abstractmethod
    async def mute(self, user_handle: str) -> ActionResult:
        """Mute a user.

        Args:
            user_handle: Handle to mute

        Returns:
            Result with success status
        """
        ...

    @abstractmethod
    async def unmute(self, user_handle: str) -> ActionResult:
        """Unmute a user.

        Args:
            user_handle: Handle to unmute

        Returns:
            Result with success status
        """
        ...

    # ==========================================================================
    # User Information
    # ==========================================================================

    @abstractmethod
    async def get_user_profile(self, handle: str) -> SocialUser | None:
        """Get profile information for a user.

        Args:
            handle: User handle to look up

        Returns:
            User profile if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_own_profile(self) -> SocialUser:
        """Get profile information for the authenticated account.

        Returns:
            Own user profile
        """
        ...
