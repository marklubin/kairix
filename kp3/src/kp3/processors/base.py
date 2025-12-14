"""Base processor classes and result types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

from kp3.db.models import Passage


@dataclass
class ProcessorResult:
    """Result of processing a group of passages.

    Actions:
    - "create": Create a new passage from the processed content
    - "update": Update an existing passage with new data
    - "pass": Skip this group, no action needed
    """

    action: Literal["create", "update", "pass"]

    # For "create" action
    content: str | None = None
    passage_type: str | None = None
    metadata: dict | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None

    # For "update" action
    passage_id: UUID | None = None
    updates: dict | None = None  # fields to update (content, metadata, embedding_qwen3, etc.)


@dataclass
class ProcessorGroup:
    """A group of passages to process together."""

    passage_ids: list[UUID]
    passages: list[Passage]
    group_key: str
    group_metadata: dict = field(default_factory=dict)


class Processor(ABC):
    """Abstract base class for passage processors."""

    @abstractmethod
    async def process(
        self,
        group: ProcessorGroup,
        config: dict,
    ) -> ProcessorResult:
        """Process a group of passages and return result.

        Args:
            group: The group of passages to process
            config: Processor-specific configuration

        Returns:
            ProcessorResult indicating what action to take
        """
        ...

    @property
    @abstractmethod
    def processor_type(self) -> str:
        """Unique identifier for this processor type."""
        ...
