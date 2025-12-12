"""Resampling VAD wrapper for sample rate mismatch."""

import logging

import numpy as np
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams

logger = logging.getLogger(__name__)


class ResamplingVADAnalyzer(SileroVADAnalyzer):
    """Silero VAD with automatic resampling from any input rate to 16kHz."""

    def __init__(self, *, input_sample_rate: int = 48000, params: VADParams | None = None):
        """Initialize with input sample rate (actual audio rate) and VAD params.

        Args:
            input_sample_rate: The sample rate of incoming audio (e.g., 48000).
            params: VAD parameters for detection thresholds and timing.
        """
        # Initialize Silero at 16kHz (its native rate)
        super().__init__(sample_rate=16000, params=params)
        self._input_sample_rate = input_sample_rate

    def set_sample_rate(self, sample_rate: int):
        """Override to capture input rate but keep Silero at 16kHz."""
        self._input_sample_rate = sample_rate
        # Call parent with 16kHz to set up internal state properly
        # This sets _sample_rate=16000 and initializes _vad_frames_num_bytes etc.
        super().set_sample_rate(16000)

    def num_frames_required(self) -> int:
        """Return frame count scaled for input sample rate.

        Silero needs 512 samples at 16kHz. At 48kHz input, we need 512 * 3 = 1536 samples
        so that after resampling we have the 512 samples Silero expects.
        """
        silero_frames = super().num_frames_required()  # 512 at 16kHz
        ratio = self._input_sample_rate / 16000
        return int(silero_frames * ratio)

    def voice_confidence(self, buffer: bytes) -> float:
        """Resample audio to 16kHz before analyzing."""
        if self._input_sample_rate == 16000:
            return super().voice_confidence(buffer)

        # Simple decimation: take every Nth sample (48kHz -> 16kHz = every 3rd)
        audio_int16 = np.frombuffer(buffer, dtype=np.int16)
        ratio = int(self._input_sample_rate / 16000)
        resampled = audio_int16[::ratio]
        resampled_bytes = resampled.tobytes()

        confidence = super().voice_confidence(resampled_bytes)
        if confidence > 0.3:
            logger.info("VAD confidence: %.2f (in=%d, out=%d)", confidence, len(audio_int16), len(resampled))
        return confidence