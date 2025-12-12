"""User turn aggregator for Pipecat pipelines.

Aggregates transcription frames into complete user turns, emitting a
UserTurnMessageFrame when the user finishes speaking.

This is a simplified alternative to Pipecat's LLMUserContextAggregator
for cases where we don't need full conversation context management
(e.g., when using Letta which manages history server-side).

State Machine:
    IDLE: Not in a turn, waiting for user to start speaking
    SPEAKING_AWAITING_TRANSCRIPT: User speaking, no transcripts yet
    SPEAKING_RECEIVED_TRANSCRIPT: User speaking, have at least one transcript
    DONE_AWAITING_TRANSCRIPT: User stopped, but expecting more transcripts (saw interim)

State handlers are defined in state_handlers.py for clarity.

Future Enhancements:
    - Flag words with low confidence scores from STT and include in UserTurnMessageFrame
      as contextual info for the LLM (e.g., "user may have said X or Y")
    - Include tone/sentiment markers from audio analysis (e.g., hesitation, excitement,
      frustration) to give LLM more context about how the user spoke, not just what
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from logging import getLogger
from typing import TYPE_CHECKING

from pipecat.frames.frames import Frame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

if TYPE_CHECKING:
    from kairix_agent.server.pipecat.state_handlers import StateHandler

logger = getLogger(__name__)


@dataclass
class UserTurnMessageFrame(Frame):
    """Frame containing the complete user message for a turn.

    Emitted when the user finishes speaking and all transcriptions
    have been aggregated.

    Attributes:
        text: The complete aggregated user message.
    """

    text: str


class UserTurnState(Enum):
    IDLE = "IDLE"
    SPEAKING_AWAITING_TRANSCRIPT = "SPEAKING_AWAITING_TRANSCRIPT"
    SPEAKING_RECEIVED_TRANSCRIPT = "SPEAKING_RECEIVED_TRANSCRIPT"
    DONE_AWAITING_TRANSCRIPT = "DONE_AWAITING_TRANSCRIPT"


class UserTurnAggregator(FrameProcessor):
    """Aggregates transcription frames into complete user turns.

    Listens for:
        - UserStartedSpeakingFrame: Marks start of turn
        - TranscriptionFrame: Final transcripts to aggregate
        - InterimTranscriptionFrame: Signals more text is coming
        - UserStoppedSpeakingFrame: Marks end of turn

    Emits:
        - UserTurnMessageFrame: When turn is complete with full text

    Uses an explicit state machine to handle the race condition where
    UserStoppedSpeakingFrame may arrive before the final TranscriptionFrame.
    """

    def __init__(
        self,
        *,
        aggregation_timeout: float = 0.5,
        name: str | None = None,
    ) -> None:
        """Initialize the user turn aggregator.

        Args:
            aggregation_timeout: Seconds to wait for final transcript after
                UserStoppedSpeakingFrame if we've seen interim results.
            name: Optional name for this processor.
        """
        super().__init__(name=name)
        self._aggregation_timeout = aggregation_timeout
        self._handlers = self._create_handlers()
        self.reset_state()

    def _create_handlers(self) -> dict[UserTurnState, StateHandler]:
        """Create handler instances for each state."""
        from kairix_agent.server.pipecat.state_handlers import (
            DoneAwaitingTranscriptHandler,
            IdleHandler,
            SpeakingAwaitingTranscriptHandler,
            SpeakingReceivedTranscriptHandler,
        )

        return {
            UserTurnState.IDLE: IdleHandler(self),
            UserTurnState.SPEAKING_AWAITING_TRANSCRIPT: SpeakingAwaitingTranscriptHandler(self),
            UserTurnState.SPEAKING_RECEIVED_TRANSCRIPT: SpeakingReceivedTranscriptHandler(self),
            UserTurnState.DONE_AWAITING_TRANSCRIPT: DoneAwaitingTranscriptHandler(self),
        }

    # -------------------------------------------------------------------------
    # State management (called by handlers)
    # -------------------------------------------------------------------------

    def reset_state(self) -> None:
        """Reset to initial idle state."""
        self._state = UserTurnState.IDLE
        self._aggregation = ""
        self._pending_interim = False
        self._done_received_at: float | None = None

    def transition_to(self, state: UserTurnState) -> None:
        """Transition to a new state."""
        logger.debug("State transition: %s → %s", self._state.value, state.value)
        self._state = state

    def append_text(self, text: str) -> None:
        """Append text to the aggregation buffer."""
        self._aggregation += text

    def set_pending_interim(self, *, pending: bool) -> None:
        """Set whether we're expecting a final transcript."""
        self._pending_interim = pending

    def has_pending_interim(self) -> bool:
        """Check if we're expecting a final transcript."""
        return self._pending_interim

    def mark_done_received(self) -> None:
        """Mark the timestamp when user stopped speaking."""
        self._done_received_at = time.monotonic()

    async def push_turn_message(self) -> None:
        """Push the aggregated turn message and reset state."""
        if self._aggregation:
            logger.info("Pushing UserTurnMessageFrame: %r", self._aggregation)
            await self.push_frame(UserTurnMessageFrame(text=self._aggregation))
        else:
            logger.debug("No aggregation to push, skipping")
        self.reset_state()

    # -------------------------------------------------------------------------
    # Frame processing
    # -------------------------------------------------------------------------

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        """Process incoming frames through the state machine.

        Args:
            frame: The incoming frame to process.
            direction: The direction of frame flow.
        """
        await super().process_frame(frame, direction)

        # Pass through upstream frames unchanged
        if direction == FrameDirection.UPSTREAM:
            await self.push_frame(frame, direction)
            return

        # Check timeout if we're in DONE_AWAITING_TRANSCRIPT
        if self._state == UserTurnState.DONE_AWAITING_TRANSCRIPT:
            await self._check_timeout()

        # Delegate to current state's handler
        handler = self._handlers[self._state]
        await handler.handle(frame, direction)

    async def _check_timeout(self) -> None:
        """Check if timeout has expired in DONE_AWAITING_TRANSCRIPT state."""
        if self._done_received_at is None:
            return
        elapsed = time.monotonic() - self._done_received_at
        if elapsed >= self._aggregation_timeout:
            logger.warning(
                "Timeout waiting for final transcript after %.2fs, pushing partial: %r",
                elapsed,
                self._aggregation,
            )
            await self.push_turn_message()
