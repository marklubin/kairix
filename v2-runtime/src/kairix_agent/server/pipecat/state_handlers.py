"""State handlers for UserTurnAggregator.

Each state in the aggregator state machine has its own handler class
that defines behavior for each possible frame type.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from logging import getLogger
from typing import TYPE_CHECKING

from pipecat.frames.frames import (
    Frame,
    InterimTranscriptionFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection

if TYPE_CHECKING:
    from kairix_agent.server.pipecat.user_turn_aggregator import UserTurnAggregator, UserTurnState

logger = getLogger(__name__)


class StateHandler(ABC):
    """Base class for state handlers."""

    def __init__(self, aggregator: UserTurnAggregator) -> None:
        self.aggregator = aggregator

    @property
    @abstractmethod
    def state(self) -> UserTurnState:
        """The state this handler manages."""
        ...

    async def handle(self, frame: Frame, direction: FrameDirection) -> None:
        """Route frame to appropriate handler method."""
        if isinstance(frame, UserStartedSpeakingFrame):
            await self.on_user_started(frame, direction)
        elif isinstance(frame, InterimTranscriptionFrame):
            await self.on_interim_transcription(frame, direction)
        elif isinstance(frame, TranscriptionFrame):
            await self.on_transcription(frame, direction)
        elif isinstance(frame, UserStoppedSpeakingFrame):
            await self.on_user_stopped(frame, direction)
        else:
            await self.on_other(frame, direction)

    async def on_user_started(
        self, frame: UserStartedSpeakingFrame, direction: FrameDirection
    ) -> None:
        """Handle UserStartedSpeakingFrame. Default: warn and pass through."""
        logger.warning("%s: Unexpected UserStartedSpeakingFrame", self.state.value)
        await self.aggregator.push_frame(frame, direction)

    async def on_interim_transcription(
        self, frame: InterimTranscriptionFrame, direction: FrameDirection
    ) -> None:
        """Handle InterimTranscriptionFrame. Default: warn and consume."""
        logger.warning("%s: Unexpected InterimTranscriptionFrame", self.state.value)

    async def on_transcription(
        self, frame: TranscriptionFrame, direction: FrameDirection
    ) -> None:
        """Handle TranscriptionFrame. Default: warn and consume."""
        logger.warning("%s: Unexpected TranscriptionFrame: %r", self.state.value, frame.text)

    async def on_user_stopped(
        self, frame: UserStoppedSpeakingFrame, direction: FrameDirection
    ) -> None:
        """Handle UserStoppedSpeakingFrame. Default: warn and pass through."""
        logger.warning("%s: Unexpected UserStoppedSpeakingFrame", self.state.value)
        await self.aggregator.push_frame(frame, direction)

    async def on_other(self, frame: Frame, direction: FrameDirection) -> None:
        """Handle all other frame types. Default: pass through."""
        await self.aggregator.push_frame(frame, direction)


class IdleHandler(StateHandler):
    """Handler for IDLE state - waiting for user to start speaking."""

    @property
    def state(self) -> UserTurnState:
        from kairix_agent.server.pipecat.user_turn_aggregator import UserTurnState
        return UserTurnState.IDLE

    async def on_user_started(
        self, frame: UserStartedSpeakingFrame, direction: FrameDirection
    ) -> None:
        """IDLE + UserStartedSpeakingFrame → SPEAKING_AWAITING_TRANSCRIPT"""
        from kairix_agent.server.pipecat.user_turn_aggregator import UserTurnState
        logger.debug("IDLE: User started speaking")
        self.aggregator.transition_to(UserTurnState.SPEAKING_AWAITING_TRANSCRIPT)
        await self.aggregator.push_frame(frame, direction)


class SpeakingAwaitingTranscriptHandler(StateHandler):
    """Handler for SPEAKING_AWAITING_TRANSCRIPT - user speaking, no transcripts yet."""

    @property
    def state(self) -> UserTurnState:
        from kairix_agent.server.pipecat.user_turn_aggregator import UserTurnState
        return UserTurnState.SPEAKING_AWAITING_TRANSCRIPT

    async def on_user_started(
        self, frame: UserStartedSpeakingFrame, direction: FrameDirection
    ) -> None:
        """Duplicate start frame - warn but pass through."""
        logger.warning("SPEAKING_AWAITING_TRANSCRIPT: Duplicate UserStartedSpeakingFrame")
        await self.aggregator.push_frame(frame, direction)

    async def on_interim_transcription(
        self, frame: InterimTranscriptionFrame, direction: FrameDirection
    ) -> None:
        """Mark that we're expecting a final transcript."""
        logger.debug("SPEAKING_AWAITING_TRANSCRIPT: Received interim")
        self.aggregator.set_pending_interim(pending=True)

    async def on_transcription(
        self, frame: TranscriptionFrame, direction: FrameDirection
    ) -> None:
        """First transcript received → SPEAKING_RECEIVED_TRANSCRIPT"""
        from kairix_agent.server.pipecat.user_turn_aggregator import UserTurnState
        logger.debug("SPEAKING_AWAITING_TRANSCRIPT: Received transcript: %r", frame.text)
        self.aggregator.append_text(frame.text)
        self.aggregator.set_pending_interim(pending=False)
        self.aggregator.transition_to(UserTurnState.SPEAKING_RECEIVED_TRANSCRIPT)

    async def on_user_stopped(
        self, frame: UserStoppedSpeakingFrame, direction: FrameDirection
    ) -> None:
        """User stopped - either wait for pending transcript or reset."""
        from kairix_agent.server.pipecat.user_turn_aggregator import UserTurnState
        if self.aggregator.has_pending_interim():
            logger.debug("SPEAKING_AWAITING_TRANSCRIPT: User stopped, waiting for final")
            self.aggregator.transition_to(UserTurnState.DONE_AWAITING_TRANSCRIPT)
            self.aggregator.mark_done_received()
        else:
            logger.debug("SPEAKING_AWAITING_TRANSCRIPT: User stopped with no transcripts")
            self.aggregator.reset_state()
        await self.aggregator.push_frame(frame, direction)


class SpeakingReceivedTranscriptHandler(StateHandler):
    """Handler for SPEAKING_RECEIVED_TRANSCRIPT - user speaking, have transcripts."""

    @property
    def state(self) -> UserTurnState:
        from kairix_agent.server.pipecat.user_turn_aggregator import UserTurnState
        return UserTurnState.SPEAKING_RECEIVED_TRANSCRIPT

    async def on_user_started(
        self, frame: UserStartedSpeakingFrame, direction: FrameDirection
    ) -> None:
        """Duplicate start frame - warn but pass through."""
        logger.warning("SPEAKING_RECEIVED_TRANSCRIPT: Duplicate UserStartedSpeakingFrame")
        await self.aggregator.push_frame(frame, direction)

    async def on_interim_transcription(
        self, frame: InterimTranscriptionFrame, direction: FrameDirection
    ) -> None:
        """Mark that more transcripts are coming."""
        logger.debug("SPEAKING_RECEIVED_TRANSCRIPT: Received interim")
        self.aggregator.set_pending_interim(pending=True)

    async def on_transcription(
        self, frame: TranscriptionFrame, direction: FrameDirection
    ) -> None:
        """Append transcript, stay in same state."""
        logger.debug("SPEAKING_RECEIVED_TRANSCRIPT: Received transcript: %r", frame.text)
        self.aggregator.append_text(frame.text)
        self.aggregator.set_pending_interim(pending=False)

    async def on_user_stopped(
        self, frame: UserStoppedSpeakingFrame, direction: FrameDirection
    ) -> None:
        """User stopped - push immediately or wait for pending."""
        from kairix_agent.server.pipecat.user_turn_aggregator import UserTurnState
        if self.aggregator.has_pending_interim():
            logger.debug("SPEAKING_RECEIVED_TRANSCRIPT: User stopped, waiting for final")
            self.aggregator.transition_to(UserTurnState.DONE_AWAITING_TRANSCRIPT)
            self.aggregator.mark_done_received()
        else:
            logger.debug("SPEAKING_RECEIVED_TRANSCRIPT: User stopped, pushing message")
            await self.aggregator.push_turn_message()
        await self.aggregator.push_frame(frame, direction)


class DoneAwaitingTranscriptHandler(StateHandler):
    """Handler for DONE_AWAITING_TRANSCRIPT - user stopped, waiting for final transcript."""

    @property
    def state(self) -> UserTurnState:
        from kairix_agent.server.pipecat.user_turn_aggregator import UserTurnState
        return UserTurnState.DONE_AWAITING_TRANSCRIPT

    async def on_user_started(
        self, frame: UserStartedSpeakingFrame, direction: FrameDirection
    ) -> None:
        """User started new turn - push what we have and start fresh."""
        from kairix_agent.server.pipecat.user_turn_aggregator import UserTurnState
        logger.debug("DONE_AWAITING_TRANSCRIPT: User started again, pushing partial")
        await self.aggregator.push_turn_message()
        self.aggregator.transition_to(UserTurnState.SPEAKING_AWAITING_TRANSCRIPT)
        await self.aggregator.push_frame(frame, direction)

    async def on_interim_transcription(
        self, frame: InterimTranscriptionFrame, direction: FrameDirection
    ) -> None:
        """Still waiting - more coming."""
        logger.debug("DONE_AWAITING_TRANSCRIPT: Received interim, continuing to wait")
        self.aggregator.set_pending_interim(pending=True)

    async def on_transcription(
        self, frame: TranscriptionFrame, direction: FrameDirection
    ) -> None:
        """Got the final - append and push."""
        logger.debug("DONE_AWAITING_TRANSCRIPT: Received final: %r, pushing", frame.text)
        self.aggregator.append_text(frame.text)
        self.aggregator.set_pending_interim(pending=False)
        await self.aggregator.push_turn_message()

    async def on_user_stopped(
        self, frame: UserStoppedSpeakingFrame, direction: FrameDirection
    ) -> None:
        """Duplicate stop - warn but pass through."""
        logger.warning("DONE_AWAITING_TRANSCRIPT: Duplicate UserStoppedSpeakingFrame")
        await self.aggregator.push_frame(frame, direction)
