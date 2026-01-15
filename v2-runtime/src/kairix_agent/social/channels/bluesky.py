"""Bluesky channel implementation using AT Protocol.

Implements the AbstractSocialChannel interface for Bluesky/AT Protocol.
Uses the atproto Python SDK for all platform interactions.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from atproto import AsyncClient, models
from atproto.exceptions import AtProtocolError

from kairix_agent.social.channels.base import (
    AbstractSocialChannel,
    ActionResult,
    PostDraft,
    PostResult,
    SocialPost,
    SocialUser,
)

logger = logging.getLogger(__name__)


class BlueskyChannel(AbstractSocialChannel):
    """Bluesky implementation using AT Protocol async client."""

    def __init__(self, handle: str, credentials: dict[str, Any]) -> None:
        """Initialize Bluesky channel.

        Args:
            handle: Bluesky handle (e.g., @user.bsky.social)
            credentials: Dict with 'identifier' and 'password' keys
        """
        self._handle = handle.lstrip("@")
        self._identifier = credentials.get("identifier", self._handle)
        self._password = credentials["password"]
        self._client: AsyncClient | None = None
        self._profile: SocialUser | None = None

    # ==========================================================================
    # Authentication
    # ==========================================================================

    async def authenticate(self) -> bool:
        """Authenticate with Bluesky."""
        self._client = AsyncClient()
        try:
            await self._client.login(self._identifier, self._password)
            logger.info("Authenticated as %s", self._handle)
            return True
        except AtProtocolError as e:
            logger.exception("Bluesky auth failed for %s: %s", self._handle, e)
            self._client = None
            return False

    async def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self._client is not None and self._client.me is not None

    def _ensure_client(self) -> AsyncClient:
        """Get authenticated client or raise."""
        if self._client is None:
            msg = "Not authenticated - call authenticate() first"
            raise RuntimeError(msg)
        return self._client

    # ==========================================================================
    # Reading Content
    # ==========================================================================

    async def get_timeline(
        self,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[SocialPost], str | None]:
        """Fetch posts from home timeline."""
        client = self._ensure_client()
        try:
            response = await client.get_timeline(limit=limit, cursor=cursor)
            posts = [self._convert_feed_view(item) for item in response.feed]
            return posts, response.cursor
        except AtProtocolError as e:
            logger.exception("Failed to get timeline: %s", e)
            return [], None

    async def get_mentions(
        self,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[SocialPost]:
        """Fetch mentions/notifications for this account."""
        client = self._ensure_client()
        try:
            response = await client.app.bsky.notification.list_notifications(
                params={"limit": limit}
            )
            mentions: list[SocialPost] = []

            for notif in response.notifications:
                # Filter to mentions and replies only
                if notif.reason not in ("mention", "reply"):
                    continue

                # Filter by time if specified
                created_at = _parse_datetime(notif.indexed_at)
                if since and created_at < since:
                    continue

                # Fetch the actual post content
                if hasattr(notif, "record") and notif.record:
                    post = self._convert_notification(notif)
                    if post:
                        mentions.append(post)

            return mentions
        except AtProtocolError as e:
            logger.exception("Failed to get mentions: %s", e)
            return []

    async def get_post(self, post_id: str) -> SocialPost | None:
        """Fetch a specific post by AT URI."""
        client = self._ensure_client()
        try:
            # post_id should be an AT URI like at://did:plc:xxx/app.bsky.feed.post/xxx
            response = await client.get_posts([post_id])
            if response.posts:
                return self._convert_post_view(response.posts[0])
            return None
        except AtProtocolError as e:
            logger.exception("Failed to get post %s: %s", post_id, e)
            return None

    async def get_thread(self, post_id: str) -> list[SocialPost]:
        """Fetch the full thread context for a post."""
        client = self._ensure_client()
        try:
            response = await client.get_post_thread(post_id)
            posts: list[SocialPost] = []

            # Extract thread posts - handle nested structure
            if hasattr(response.thread, "post"):
                posts.append(self._convert_post_view(response.thread.post))

            # Get replies if available
            if hasattr(response.thread, "replies") and response.thread.replies:
                for reply in response.thread.replies:
                    if hasattr(reply, "post"):
                        posts.append(self._convert_post_view(reply.post))

            return posts
        except AtProtocolError as e:
            logger.exception("Failed to get thread %s: %s", post_id, e)
            return []

    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[SocialPost]:
        """Search posts on Bluesky."""
        client = self._ensure_client()
        try:
            response = await client.app.bsky.feed.search_posts(
                params={"q": query, "limit": limit}
            )
            return [self._convert_post_view(post) for post in response.posts]
        except AtProtocolError as e:
            logger.exception("Search failed for '%s': %s", query, e)
            return []

    # ==========================================================================
    # Creating Content
    # ==========================================================================

    async def post(self, draft: PostDraft) -> PostResult:
        """Submit a new post or reply."""
        client = self._ensure_client()
        try:
            if draft.reply_to_id:
                # Fetch parent post to construct reply ref
                parent_response = await client.get_posts([draft.reply_to_id])
                if not parent_response.posts:
                    return PostResult(
                        success=False,
                        error=f"Parent post not found: {draft.reply_to_id}",
                    )

                parent = parent_response.posts[0]

                # Build reply reference
                reply_ref = models.AppBskyFeedPost.ReplyRef(
                    root=models.create_strong_ref(parent),
                    parent=models.create_strong_ref(parent),
                )

                result = await client.send_post(
                    text=draft.content,
                    reply_to=reply_ref,
                )
            elif draft.quote_id:
                # Quote post
                result = await client.send_post(
                    text=draft.content,
                    embed=models.AppBskyEmbedRecord.Main(
                        record=models.ComAtprotoRepoStrongRef.Main(
                            uri=draft.quote_id,
                            cid="",  # Will be resolved
                        )
                    ),
                )
            else:
                # Regular post
                result = await client.send_post(text=draft.content)

            return PostResult(success=True, external_id=result.uri)
        except AtProtocolError as e:
            logger.exception("Failed to post: %s", e)
            return PostResult(success=False, error=str(e))

    # ==========================================================================
    # Social Actions
    # ==========================================================================

    async def like(self, post_id: str) -> ActionResult:
        """Like a post."""
        client = self._ensure_client()
        try:
            await client.like(post_id)
            return ActionResult(success=True)
        except AtProtocolError as e:
            logger.exception("Failed to like %s: %s", post_id, e)
            return ActionResult(success=False, error=str(e))

    async def unlike(self, post_id: str) -> ActionResult:
        """Remove like from a post."""
        client = self._ensure_client()
        try:
            await client.unlike(post_id)
            return ActionResult(success=True)
        except AtProtocolError as e:
            logger.exception("Failed to unlike %s: %s", post_id, e)
            return ActionResult(success=False, error=str(e))

    async def repost(self, post_id: str) -> ActionResult:
        """Repost a post."""
        client = self._ensure_client()
        try:
            await client.repost(post_id)
            return ActionResult(success=True)
        except AtProtocolError as e:
            logger.exception("Failed to repost %s: %s", post_id, e)
            return ActionResult(success=False, error=str(e))

    async def unrepost(self, post_id: str) -> ActionResult:
        """Remove repost."""
        client = self._ensure_client()
        try:
            await client.unrepost(post_id)
            return ActionResult(success=True)
        except AtProtocolError as e:
            logger.exception("Failed to unrepost %s: %s", post_id, e)
            return ActionResult(success=False, error=str(e))

    async def follow(self, user_handle: str) -> ActionResult:
        """Follow a user."""
        client = self._ensure_client()
        try:
            await client.follow(user_handle.lstrip("@"))
            return ActionResult(success=True)
        except AtProtocolError as e:
            logger.exception("Failed to follow %s: %s", user_handle, e)
            return ActionResult(success=False, error=str(e))

    async def unfollow(self, user_handle: str) -> ActionResult:
        """Unfollow a user."""
        client = self._ensure_client()
        try:
            await client.unfollow(user_handle.lstrip("@"))
            return ActionResult(success=True)
        except AtProtocolError as e:
            logger.exception("Failed to unfollow %s: %s", user_handle, e)
            return ActionResult(success=False, error=str(e))

    async def block(self, user_handle: str) -> ActionResult:
        """Block a user."""
        client = self._ensure_client()
        try:
            # Resolve handle to DID first
            profile = await client.get_profile(user_handle.lstrip("@"))
            await client.app.bsky.graph.block.create(
                client.me.did,
                models.AppBskyGraphBlock.Record(
                    subject=profile.did,
                    created_at=client.get_current_time_iso(),
                ),
            )
            return ActionResult(success=True)
        except AtProtocolError as e:
            logger.exception("Failed to block %s: %s", user_handle, e)
            return ActionResult(success=False, error=str(e))

    async def unblock(self, user_handle: str) -> ActionResult:
        """Unblock a user."""
        self._ensure_client()  # Verify authenticated
        # This requires finding and deleting the block record
        # For now, return not implemented
        _ = user_handle  # Suppress unused warning
        return ActionResult(success=False, error="Unblock not yet implemented")

    async def mute(self, user_handle: str) -> ActionResult:
        """Mute a user."""
        client = self._ensure_client()
        try:
            await client.mute(user_handle.lstrip("@"))
            return ActionResult(success=True)
        except AtProtocolError as e:
            logger.exception("Failed to mute %s: %s", user_handle, e)
            return ActionResult(success=False, error=str(e))

    async def unmute(self, user_handle: str) -> ActionResult:
        """Unmute a user."""
        client = self._ensure_client()
        try:
            await client.unmute(user_handle.lstrip("@"))
            return ActionResult(success=True)
        except AtProtocolError as e:
            logger.exception("Failed to unmute %s: %s", user_handle, e)
            return ActionResult(success=False, error=str(e))

    # ==========================================================================
    # User Information
    # ==========================================================================

    async def get_user_profile(self, handle: str) -> SocialUser | None:
        """Get profile information for a user."""
        client = self._ensure_client()
        try:
            profile = await client.get_profile(handle.lstrip("@"))
            return self._convert_profile(profile)
        except AtProtocolError as e:
            logger.exception("Failed to get profile for %s: %s", handle, e)
            return None

    async def get_own_profile(self) -> SocialUser:
        """Get profile information for the authenticated account."""
        if self._profile:
            return self._profile

        client = self._ensure_client()
        profile = await client.get_profile(client.me.did)
        self._profile = self._convert_profile(profile)
        return self._profile

    # ==========================================================================
    # Conversion Helpers
    # ==========================================================================

    def _convert_feed_view(self, feed_item: Any) -> SocialPost:
        """Convert a feed view post to SocialPost."""
        post = feed_item.post
        return self._convert_post_view(post)

    def _convert_post_view(self, post: Any) -> SocialPost:
        """Convert a PostView to SocialPost."""
        record = post.record

        # Extract reply context if present
        parent_id = None
        root_id = None
        if hasattr(record, "reply") and record.reply:
            parent_id = record.reply.parent.uri if record.reply.parent else None
            root_id = record.reply.root.uri if record.reply.root else None

        return SocialPost(
            external_id=post.uri,
            author_handle=post.author.handle,
            author_display_name=post.author.display_name or post.author.handle,
            author_did=post.author.did,
            content=record.text if hasattr(record, "text") else "",
            created_at=_parse_datetime(post.indexed_at),
            reply_count=post.reply_count or 0,
            repost_count=post.repost_count or 0,
            like_count=post.like_count or 0,
            parent_id=parent_id,
            root_id=root_id,
            has_media=bool(hasattr(record, "embed") and record.embed),
            metadata={
                "cid": post.cid,
                "labels": [label.val for label in (post.labels or [])],
            },
        )

    def _convert_notification(self, notif: Any) -> SocialPost | None:
        """Convert a notification to SocialPost."""
        if not hasattr(notif, "record") or not notif.record:
            return None

        record = notif.record
        return SocialPost(
            external_id=notif.uri,
            author_handle=notif.author.handle,
            author_display_name=notif.author.display_name or notif.author.handle,
            author_did=notif.author.did,
            content=record.text if hasattr(record, "text") else "",
            created_at=_parse_datetime(notif.indexed_at),
            reply_count=0,
            repost_count=0,
            like_count=0,
            parent_id=None,
            root_id=None,
            metadata={
                "reason": notif.reason,
                "is_read": notif.is_read,
            },
        )

    def _convert_profile(self, profile: Any) -> SocialUser:
        """Convert a ProfileViewDetailed to SocialUser."""
        return SocialUser(
            handle=profile.handle,
            display_name=profile.display_name or profile.handle,
            did=profile.did,
            bio=profile.description,
            follower_count=profile.followers_count or 0,
            following_count=profile.follows_count or 0,
            avatar_url=profile.avatar,
            metadata={
                "posts_count": profile.posts_count,
                "labels": [label.val for label in (profile.labels or [])],
            },
        )


def _parse_datetime(iso_string: str) -> datetime:
    """Parse ISO datetime string to datetime object."""
    from datetime import UTC

    # Handle both formats: with and without microseconds
    try:
        return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    except ValueError:
        # Fallback for edge cases
        return datetime.now(UTC)
