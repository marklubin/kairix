"""Data models for progressive summarization system."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class SummaryType(str, Enum):
    """Type of summary - determines rollup level."""

    SESSION = "session"
    DAILY = "daily"  # Phase 2
    WEEKLY = "weekly"  # Phase 2
    TOPIC = "topic"  # Phase 3

    def to_tag(self) -> str:
        """Convert to Letta passage tag format."""
        return f"summary:{self.value}"


class ConversationSummary(BaseModel):
    """Summary stored in Letta archival memory.

    Stored as a passage with:
    - text: The summary content
    - tags: [summary:{type}]
    - timestamp: period_end (for datetime filtering)
    """

    summary_id: UUID
    summary_type: SummaryType
    agent_id: str
    period_start: datetime
    period_end: datetime
    summary_text: str
    message_count: int
    source_message_ids: list[str]  # For validation/debugging
    created_at: datetime

    def to_passage_text(self) -> str:
        """Format summary for Letta archival storage."""
        return f"""[{self.summary_type.value.upper()}_SUMMARY]
Period: {self.period_start.isoformat()} to {self.period_end.isoformat()}
Messages: {self.message_count}

{self.summary_text}
[/{self.summary_type.value.upper()}_SUMMARY]"""

    def to_tag(self) -> str:
        """Get the Letta passage tag for this summary."""
        return self.summary_type.to_tag()


class SummarizationCursor(BaseModel):
    """Tracks summarization progress per agent. Stored in Redis.

    Key format: summarization_cursor:{agent_id}
    """

    agent_id: str
    last_summarized_at: datetime
    last_message_id: str

    def redis_key(self) -> str:
        """Get Redis key for this cursor."""
        return f"summarization_cursor:{self.agent_id}"
