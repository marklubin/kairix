"""Pydantic schemas for event payloads."""

from pydantic import BaseModel


class SessionBoundaryPayload(BaseModel):
    """Payload for SESSION_BOUNDARY events.

    Emitted every time the boundary check runs for an agent.
    """

    boundary_detected: bool
    gap_minutes: float
    message_count: int


class SummaryCompletePayload(BaseModel):
    """Payload for SUMMARY_COMPLETE events."""

    message_count: int
    summary: str


class InsightsCompletePayload(BaseModel):
    """Payload for INSIGHTS_COMPLETE events."""

    triggered: bool
    response: str | None = None


class MemoryBlockPayload(BaseModel):
    """A single memory block from the agent's core memory."""

    label: str
    value: str
    updated_at: str | None = None


class ContextStatePayload(BaseModel):
    """Payload for CONTEXT_STATE events.

    Contains the full list of memory blocks for the agent.
    Note: The DB stores only lightweight metadata (block_count),
    while the full blocks are fetched fresh from Letta when dispatching.
    """

    blocks: list[MemoryBlockPayload]
