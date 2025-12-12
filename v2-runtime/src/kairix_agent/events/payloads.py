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
