"""Social channel implementations.

Provides channel adapters for different social platforms.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from kairix_agent.social.channels.base import (
    AbstractSocialChannel,
    PostDraft,
    PostResult,
    SocialPost,
    SocialUser,
)
from kairix_agent.social.crypto import decrypt_credentials

if TYPE_CHECKING:
    from kairix_agent.social.models import SocialChannel


def create_channel(db_channel: SocialChannel) -> AbstractSocialChannel:
    """Factory to create channel instance from DB model.

    Args:
        db_channel: Database model with encrypted credentials

    Returns:
        Authenticated channel instance ready for use

    Raises:
        ValueError: If channel type is not supported
    """
    from kairix_agent.social.channels.bluesky import BlueskyChannel
    from kairix_agent.social.models import SocialChannelType

    credentials = decrypt_credentials(db_channel.credentials_encrypted)

    if db_channel.channel_type == SocialChannelType.BLUESKY.value:
        return BlueskyChannel(db_channel.handle, credentials)

    msg = f"Unknown channel type: {db_channel.channel_type}"
    raise ValueError(msg)


__all__ = [
    "AbstractSocialChannel",
    "PostDraft",
    "PostResult",
    "SocialPost",
    "SocialUser",
    "create_channel",
]
