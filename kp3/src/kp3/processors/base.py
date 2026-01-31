"""Base processor classes and result types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Generic, Literal, TypeVar
from uuid import UUID

from kp3.db.models import Passage

# Type variable for processor-specific config
ConfigT = TypeVar("ConfigT")


@dataclass
class ProcessorResult:
    """Result of processing a group of passages.

    Actions:
    - "create": Create a new passage from the processed content
    - "update": Update an existing passage with new data
    - "pass": Skip this group, no action needed
    """

    action: Literal["create", "update", "pass"]

    # For "create" action - processor provides content, run config provides passage_type
    content: str | None = None
    metadata: dict | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None

    # For "update" action
    passage_id: UUID | None = None
    updates: dict | None = None  # fields to update (content, metadata, embedding_openai, etc.)


@dataclass
class ProcessorGroup:
    """A group of passages to process together."""

    passage_ids: list[UUID]
    passages: list[Passage]
    group_key: str
    group_metadata: dict = field(default_factory=dict)


class Processor(ABC, Generic[ConfigT]):
    """Abstract base class for passage processors."""

    @abstractmethod
    async def process(
        self,
        group: ProcessorGroup,
        config: ConfigT,
    ) -> ProcessorResult:
        """Process a group of passages and return result.

        Args:
            group: The group of passages to process
            config: Typed processor-specific configuration

        Returns:
            ProcessorResult indicating what action to take
        """
        ...

    @classmethod
    @abstractmethod
    def parse_config(cls, raw: dict) -> ConfigT:
        """Parse raw config dict into typed config object."""
        ...

    @property
    @abstractmethod
    def processor_type(self) -> str:
        """Unique identifier for this processor type."""
        ...
