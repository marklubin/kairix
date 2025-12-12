"""Tests for UserTurnAggregator state machine."""

from unittest.mock import AsyncMock

import pytest
from pipecat.frames.frames import (
    InterimTranscriptionFrame,
    TextFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection

from kairix_agent.server.pipecat.user_turn_aggregator import (
    UserTurnAggregator,
    UserTurnMessageFrame,
    UserTurnState,
)


@pytest.fixture
def aggregator() -> UserTurnAggregator:
    """Create a fresh aggregator for each test."""
    return UserTurnAggregator(aggregation_timeout=0.5)


@pytest.fixture
def mock_push_frame(aggregator: UserTurnAggregator) -> AsyncMock:
    """Mock the push_frame method to capture outputs."""
    mock = AsyncMock()
    aggregator.push_frame = mock
    return mock


def make_transcription(text: str) -> TranscriptionFrame:
    """Helper to create a TranscriptionFrame."""
    return TranscriptionFrame(text=text, user_id="test-user", timestamp="0")


def make_interim(text: str) -> InterimTranscriptionFrame:
    """Helper to create an InterimTranscriptionFrame."""
    return InterimTranscriptionFrame(text=text, user_id="test-user", timestamp="0")


class TestIdleState:
    """Tests for IDLE state transitions."""

    @pytest.mark.asyncio
    async def test_user_started_transitions_to_speaking_awaiting(
        self, aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """IDLE + UserStartedSpeakingFrame → SPEAKING_AWAITING_TRANSCRIPT"""
        assert aggregator._state == UserTurnState.IDLE

        frame = UserStartedSpeakingFrame()
        await aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert aggregator._state == UserTurnState.SPEAKING_AWAITING_TRANSCRIPT
        mock_push_frame.assert_called_once_with(frame, FrameDirection.DOWNSTREAM)

    @pytest.mark.asyncio
    async def test_transcription_in_idle_is_ignored(
        self, aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """IDLE + TranscriptionFrame → stay IDLE, don't pass through"""
        frame = make_transcription("unexpected")
        await aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert aggregator._state == UserTurnState.IDLE
        assert aggregator._aggregation == ""
        mock_push_frame.assert_not_called()

    @pytest.mark.asyncio
    async def test_interim_in_idle_is_ignored(
        self, aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """IDLE + InterimTranscriptionFrame → stay IDLE, don't pass through"""
        frame = make_interim("unexpected")
        await aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert aggregator._state == UserTurnState.IDLE
        mock_push_frame.assert_not_called()

    @pytest.mark.asyncio
    async def test_other_frames_pass_through(
        self, aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """IDLE + other frame → pass through unchanged"""
        frame = TextFrame(text="hello")
        await aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert aggregator._state == UserTurnState.IDLE
        mock_push_frame.assert_called_once_with(frame, FrameDirection.DOWNSTREAM)


class TestSpeakingAwaitingTranscriptState:
    """Tests for SPEAKING_AWAITING_TRANSCRIPT state transitions."""

    @pytest.fixture
    def speaking_aggregator(self, aggregator: UserTurnAggregator) -> UserTurnAggregator:
        """Aggregator already in SPEAKING_AWAITING_TRANSCRIPT state."""
        aggregator._state = UserTurnState.SPEAKING_AWAITING_TRANSCRIPT
        return aggregator

    @pytest.mark.asyncio
    async def test_interim_sets_pending_flag(
        self, speaking_aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """SPEAKING_AWAITING + InterimTranscriptionFrame → set pending, stay"""
        frame = make_interim("partial")
        await speaking_aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert speaking_aggregator._state == UserTurnState.SPEAKING_AWAITING_TRANSCRIPT
        assert speaking_aggregator._pending_interim is True
        mock_push_frame.assert_not_called()

    @pytest.mark.asyncio
    async def test_transcription_transitions_to_received(
        self, speaking_aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """SPEAKING_AWAITING + TranscriptionFrame → SPEAKING_RECEIVED_TRANSCRIPT"""
        frame = make_transcription("hello world")
        await speaking_aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert speaking_aggregator._state == UserTurnState.SPEAKING_RECEIVED_TRANSCRIPT
        assert speaking_aggregator._aggregation == "hello world"
        assert speaking_aggregator._pending_interim is False
        mock_push_frame.assert_not_called()

    @pytest.mark.asyncio
    async def test_user_stopped_no_pending_resets_to_idle(
        self, speaking_aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """SPEAKING_AWAITING + UserStoppedSpeakingFrame (no pending) → IDLE"""
        speaking_aggregator._pending_interim = False
        frame = UserStoppedSpeakingFrame()
        await speaking_aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert speaking_aggregator._state == UserTurnState.IDLE
        mock_push_frame.assert_called_once_with(frame, FrameDirection.DOWNSTREAM)

    @pytest.mark.asyncio
    async def test_user_stopped_with_pending_transitions_to_done_awaiting(
        self, speaking_aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """SPEAKING_AWAITING + UserStoppedSpeakingFrame (pending) → DONE_AWAITING"""
        speaking_aggregator._pending_interim = True
        frame = UserStoppedSpeakingFrame()
        await speaking_aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert speaking_aggregator._state == UserTurnState.DONE_AWAITING_TRANSCRIPT
        assert speaking_aggregator._done_received_at is not None
        mock_push_frame.assert_called_once_with(frame, FrameDirection.DOWNSTREAM)


class TestSpeakingReceivedTranscriptState:
    """Tests for SPEAKING_RECEIVED_TRANSCRIPT state transitions."""

    @pytest.fixture
    def received_aggregator(self, aggregator: UserTurnAggregator) -> UserTurnAggregator:
        """Aggregator in SPEAKING_RECEIVED_TRANSCRIPT with some text."""
        aggregator._state = UserTurnState.SPEAKING_RECEIVED_TRANSCRIPT
        aggregator._aggregation = "hello "
        return aggregator

    @pytest.mark.asyncio
    async def test_transcription_appends_and_stays(
        self, received_aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """SPEAKING_RECEIVED + TranscriptionFrame → append, stay"""
        frame = make_transcription("world")
        await received_aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert received_aggregator._state == UserTurnState.SPEAKING_RECEIVED_TRANSCRIPT
        assert received_aggregator._aggregation == "hello world"
        mock_push_frame.assert_not_called()

    @pytest.mark.asyncio
    async def test_interim_sets_pending(
        self, received_aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """SPEAKING_RECEIVED + InterimTranscriptionFrame → set pending"""
        frame = make_interim("partial")
        await received_aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert received_aggregator._pending_interim is True
        mock_push_frame.assert_not_called()

    @pytest.mark.asyncio
    async def test_user_stopped_no_pending_pushes_message(
        self, received_aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """SPEAKING_RECEIVED + UserStoppedSpeakingFrame (no pending) → push and IDLE"""
        received_aggregator._pending_interim = False
        frame = UserStoppedSpeakingFrame()
        await received_aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert received_aggregator._state == UserTurnState.IDLE
        assert received_aggregator._aggregation == ""

        # Should have pushed UserTurnMessageFrame then the stop frame
        calls = mock_push_frame.call_args_list
        assert len(calls) == 2
        assert isinstance(calls[0][0][0], UserTurnMessageFrame)
        assert calls[0][0][0].text == "hello "
        assert calls[1][0][0] == frame

    @pytest.mark.asyncio
    async def test_user_stopped_with_pending_transitions_to_done_awaiting(
        self, received_aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """SPEAKING_RECEIVED + UserStoppedSpeakingFrame (pending) → DONE_AWAITING"""
        received_aggregator._pending_interim = True
        frame = UserStoppedSpeakingFrame()
        await received_aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert received_aggregator._state == UserTurnState.DONE_AWAITING_TRANSCRIPT
        assert received_aggregator._done_received_at is not None
        # Message not pushed yet - waiting for final
        calls = mock_push_frame.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == frame


class TestDoneAwaitingTranscriptState:
    """Tests for DONE_AWAITING_TRANSCRIPT state transitions."""

    @pytest.fixture
    def done_awaiting_aggregator(self, aggregator: UserTurnAggregator) -> UserTurnAggregator:
        """Aggregator in DONE_AWAITING_TRANSCRIPT with buffered text."""
        aggregator._state = UserTurnState.DONE_AWAITING_TRANSCRIPT
        aggregator._aggregation = "hello "
        aggregator._pending_interim = True
        aggregator.mark_done_received()
        return aggregator

    @pytest.mark.asyncio
    async def test_transcription_pushes_and_resets(
        self, done_awaiting_aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """DONE_AWAITING + TranscriptionFrame → append, push, IDLE"""
        frame = make_transcription("world")
        await done_awaiting_aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert done_awaiting_aggregator._state == UserTurnState.IDLE
        assert done_awaiting_aggregator._aggregation == ""

        mock_push_frame.assert_called_once()
        pushed = mock_push_frame.call_args[0][0]
        assert isinstance(pushed, UserTurnMessageFrame)
        assert pushed.text == "hello world"

    @pytest.mark.asyncio
    async def test_user_started_pushes_partial_and_starts_new_turn(
        self, done_awaiting_aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """DONE_AWAITING + UserStartedSpeakingFrame → push partial, start new turn"""
        frame = UserStartedSpeakingFrame()
        await done_awaiting_aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert done_awaiting_aggregator._state == UserTurnState.SPEAKING_AWAITING_TRANSCRIPT

        calls = mock_push_frame.call_args_list
        assert len(calls) == 2
        # First: push the partial message
        assert isinstance(calls[0][0][0], UserTurnMessageFrame)
        assert calls[0][0][0].text == "hello "
        # Second: pass through the start frame
        assert calls[1][0][0] == frame

    @pytest.mark.asyncio
    async def test_interim_keeps_waiting(
        self, done_awaiting_aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """DONE_AWAITING + InterimTranscriptionFrame → stay, keep pending"""
        frame = make_interim("more coming")
        await done_awaiting_aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        assert done_awaiting_aggregator._state == UserTurnState.DONE_AWAITING_TRANSCRIPT
        assert done_awaiting_aggregator._pending_interim is True
        mock_push_frame.assert_not_called()


class TestTimeoutBehavior:
    """Tests for timeout behavior in DONE_AWAITING_TRANSCRIPT state."""

    @pytest.mark.asyncio
    async def test_timeout_pushes_partial(
        self, aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """After timeout expires, next frame triggers push of partial message."""
        # Set up aggregator in DONE_AWAITING state with expired timeout
        aggregator._state = UserTurnState.DONE_AWAITING_TRANSCRIPT
        aggregator._aggregation = "partial message"
        aggregator._done_received_at = 0  # Long ago - timeout expired

        # Any frame should trigger the timeout check
        frame = TextFrame(text="unrelated")
        await aggregator.process_frame(frame, FrameDirection.DOWNSTREAM)

        # Should have pushed the partial message
        assert aggregator._state == UserTurnState.IDLE
        calls = mock_push_frame.call_args_list
        assert len(calls) == 2
        assert isinstance(calls[0][0][0], UserTurnMessageFrame)
        assert calls[0][0][0].text == "partial message"


class TestFullConversationFlow:
    """Integration tests for complete conversation flows."""

    @pytest.mark.asyncio
    async def test_simple_utterance(
        self, aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """Test: user speaks, we get transcript, user stops → push message."""
        # User starts speaking
        await aggregator.process_frame(
            UserStartedSpeakingFrame(), FrameDirection.DOWNSTREAM
        )
        assert aggregator._state == UserTurnState.SPEAKING_AWAITING_TRANSCRIPT

        # Get a transcript
        await aggregator.process_frame(
            make_transcription("hello world"), FrameDirection.DOWNSTREAM
        )
        assert aggregator._state == UserTurnState.SPEAKING_RECEIVED_TRANSCRIPT
        assert aggregator._aggregation == "hello world"

        # User stops speaking
        await aggregator.process_frame(
            UserStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM
        )
        assert aggregator._state == UserTurnState.IDLE

        # Check we pushed the message
        calls = [c for c in mock_push_frame.call_args_list
                 if isinstance(c[0][0], UserTurnMessageFrame)]
        assert len(calls) == 1
        assert calls[0][0][0].text == "hello world"

    @pytest.mark.asyncio
    async def test_multiple_transcripts_per_turn(
        self, aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """Test: multiple final transcripts aggregated into single message."""
        await aggregator.process_frame(
            UserStartedSpeakingFrame(), FrameDirection.DOWNSTREAM
        )

        # Multiple transcripts (Deepgram sends finals at sentence boundaries)
        await aggregator.process_frame(
            make_transcription("Hello. "), FrameDirection.DOWNSTREAM
        )
        await aggregator.process_frame(
            make_transcription("How are you? "), FrameDirection.DOWNSTREAM
        )
        await aggregator.process_frame(
            make_transcription("I'm fine."), FrameDirection.DOWNSTREAM
        )

        assert aggregator._aggregation == "Hello. How are you? I'm fine."

        # User stops
        await aggregator.process_frame(
            UserStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM
        )

        # Check aggregated message
        calls = [c for c in mock_push_frame.call_args_list
                 if isinstance(c[0][0], UserTurnMessageFrame)]
        assert len(calls) == 1
        assert calls[0][0][0].text == "Hello. How are you? I'm fine."

    @pytest.mark.asyncio
    async def test_race_condition_stop_before_final(
        self, aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """Test: UserStoppedSpeakingFrame arrives before final transcript."""
        await aggregator.process_frame(
            UserStartedSpeakingFrame(), FrameDirection.DOWNSTREAM
        )

        # Got interim (signals more coming)
        await aggregator.process_frame(
            make_interim("hell"), FrameDirection.DOWNSTREAM
        )
        assert aggregator._pending_interim is True

        # User stops before final arrives
        await aggregator.process_frame(
            UserStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM
        )
        assert aggregator._state == UserTurnState.DONE_AWAITING_TRANSCRIPT

        # Final arrives after stop
        await aggregator.process_frame(
            make_transcription("hello"), FrameDirection.DOWNSTREAM
        )
        assert aggregator._state == UserTurnState.IDLE

        # Should have pushed complete message
        calls = [c for c in mock_push_frame.call_args_list
                 if isinstance(c[0][0], UserTurnMessageFrame)]
        assert len(calls) == 1
        assert calls[0][0][0].text == "hello"

    @pytest.mark.asyncio
    async def test_upstream_frames_pass_through_unchanged(
        self, aggregator: UserTurnAggregator, mock_push_frame: AsyncMock
    ) -> None:
        """Upstream frames should pass through without state changes."""
        # Put aggregator in a non-idle state
        aggregator._state = UserTurnState.SPEAKING_RECEIVED_TRANSCRIPT
        aggregator._aggregation = "some text"

        frame = TextFrame(text="upstream")
        await aggregator.process_frame(frame, FrameDirection.UPSTREAM)

        # State unchanged
        assert aggregator._state == UserTurnState.SPEAKING_RECEIVED_TRANSCRIPT
        assert aggregator._aggregation == "some text"
        mock_push_frame.assert_called_once_with(frame, FrameDirection.UPSTREAM)
