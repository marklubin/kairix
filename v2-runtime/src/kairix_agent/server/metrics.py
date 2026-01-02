"""OpenTelemetry metrics for voice pipeline.

Provides instrumentation for tracking voice sessions, STT/LLM/TTS latency,
interruptions, and conversation turns.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)

# Global meter (lazy initialized)
_meter: metrics.Meter | None = None
_initialized: bool = False


def _is_metrics_enabled() -> bool:
    """Check if metrics export is enabled via environment."""
    return os.environ.get("ENABLE_METRICS", "").lower() in ("1", "true", "yes")


def init_metrics() -> None:
    """Initialize the metrics provider with OTLP exporter.

    Call this once at server startup. Safe to call multiple times.
    """
    global _meter, _initialized  # noqa: PLW0603

    if _initialized:
        return

    _initialized = True

    if not _is_metrics_enabled():
        logger.info("Server metrics disabled (ENABLE_METRICS not set)")
        _meter = metrics.get_meter("kairix-server")
        return

    try:
        # Import OTLP exporter only when needed (may not be installed)
        import base64  # noqa: PLC0415

        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (  # noqa: PLC0415
            OTLPMetricExporter,
        )
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader  # noqa: PLC0415

        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:5081")

        # OpenObserve requires Basic auth + organization/stream headers
        otel_user = os.environ.get("OTEL_EXPORTER_OTLP_USER", "admin@kairix.local")
        otel_pass = os.environ.get("OTEL_EXPORTER_OTLP_PASSWORD", "kairix123")
        auth_string = f"{otel_user}:{otel_pass}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        headers = (
            ("authorization", f"Basic {auth_bytes}"),
            ("organization", "default"),
            ("stream-name", "kairix_voice_metrics"),
        )

        exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True, headers=headers)
        reader = PeriodicExportingMetricReader(exporter, export_interval_millis=30000)
        provider = MeterProvider(
            resource=Resource.create({"service.name": "kairix-server"}),
            metric_readers=[reader],
        )
        metrics.set_meter_provider(provider)
        _meter = metrics.get_meter("kairix-server")

        logger.info("Server metrics initialized, exporting to %s", endpoint)

    except ImportError:
        logger.warning("OTLP metric exporter not available, server metrics disabled")
        _meter = metrics.get_meter("kairix-server")
    except Exception:
        logger.exception("Failed to initialize server metrics")
        _meter = metrics.get_meter("kairix-server")


def get_meter() -> metrics.Meter:
    """Get the metrics meter, initializing if needed."""
    if _meter is None:
        init_metrics()

    assert _meter is not None  # noqa: S101
    return _meter


# ============================================================================
# Lazy instrument accessors (created on first use)
# ============================================================================

_session_counter: metrics.Counter | None = None
_session_duration: metrics.Histogram | None = None
_turn_counter: metrics.Counter | None = None
_interruption_counter: metrics.Counter | None = None
_stt_latency: metrics.Histogram | None = None
_llm_latency: metrics.Histogram | None = None
_tts_latency: metrics.Histogram | None = None
_llm_ttfb: metrics.Histogram | None = None


def _get_session_counter() -> metrics.Counter:
    global _session_counter  # noqa: PLW0603
    if _session_counter is None:
        _session_counter = get_meter().create_counter(
            "voice_sessions_total",
            description="Total voice session count",
        )
    return _session_counter


def _get_session_duration() -> metrics.Histogram:
    global _session_duration  # noqa: PLW0603
    if _session_duration is None:
        _session_duration = get_meter().create_histogram(
            "voice_session_duration_seconds",
            description="Voice session duration in seconds",
        )
    return _session_duration


def _get_turn_counter() -> metrics.Counter:
    global _turn_counter  # noqa: PLW0603
    if _turn_counter is None:
        _turn_counter = get_meter().create_counter(
            "voice_turns_total",
            description="Total conversation turns",
        )
    return _turn_counter


def _get_interruption_counter() -> metrics.Counter:
    global _interruption_counter  # noqa: PLW0603
    if _interruption_counter is None:
        _interruption_counter = get_meter().create_counter(
            "voice_interruptions_total",
            description="Total user interruptions",
        )
    return _interruption_counter


def _get_stt_latency() -> metrics.Histogram:
    global _stt_latency  # noqa: PLW0603
    if _stt_latency is None:
        _stt_latency = get_meter().create_histogram(
            "voice_stt_latency_seconds",
            description="Speech-to-text latency (audio end to transcript)",
        )
    return _stt_latency


def _get_llm_latency() -> metrics.Histogram:
    global _llm_latency  # noqa: PLW0603
    if _llm_latency is None:
        _llm_latency = get_meter().create_histogram(
            "voice_llm_latency_seconds",
            description="LLM processing latency (transcript to response end)",
        )
    return _llm_latency


def _get_tts_latency() -> metrics.Histogram:
    global _tts_latency  # noqa: PLW0603
    if _tts_latency is None:
        _tts_latency = get_meter().create_histogram(
            "voice_tts_latency_seconds",
            description="Text-to-speech latency (text to audio)",
        )
    return _tts_latency


def _get_llm_ttfb() -> metrics.Histogram:
    global _llm_ttfb  # noqa: PLW0603
    if _llm_ttfb is None:
        _llm_ttfb = get_meter().create_histogram(
            "voice_llm_ttfb_seconds",
            description="LLM time to first byte (transcript to first token)",
        )
    return _llm_ttfb


# ============================================================================
# Recording functions
# ============================================================================


def record_session_start(agent_id: str) -> None:
    """Record a voice session starting."""
    _get_session_counter().add(1, {"agent_id": agent_id, "status": "started"})


def record_session_end(agent_id: str, duration: float, *, error: bool = False) -> None:
    """Record a voice session ending.

    Args:
        agent_id: The agent ID.
        duration: Session duration in seconds.
        error: Whether the session ended due to an error.
    """
    status = "error" if error else "completed"
    _get_session_counter().add(1, {"agent_id": agent_id, "status": status})
    _get_session_duration().record(duration, {"agent_id": agent_id})


def record_turn(agent_id: str) -> None:
    """Record a conversation turn."""
    _get_turn_counter().add(1, {"agent_id": agent_id})


def record_interruption(agent_id: str) -> None:
    """Record a user interruption."""
    _get_interruption_counter().add(1, {"agent_id": agent_id})


def record_stt_latency(latency: float, agent_id: str) -> None:
    """Record STT latency in seconds."""
    _get_stt_latency().record(latency, {"agent_id": agent_id})


def record_llm_latency(latency: float, agent_id: str) -> None:
    """Record LLM latency in seconds."""
    _get_llm_latency().record(latency, {"agent_id": agent_id})


def record_llm_ttfb(latency: float, agent_id: str) -> None:
    """Record LLM time to first byte in seconds."""
    _get_llm_ttfb().record(latency, {"agent_id": agent_id})


def record_tts_latency(latency: float, agent_id: str) -> None:
    """Record TTS latency in seconds."""
    _get_tts_latency().record(latency, {"agent_id": agent_id})


# ============================================================================
# Context managers for timing
# ============================================================================


@contextmanager
def time_stt(agent_id: str) -> Iterator[None]:
    """Context manager to time STT latency."""
    start = time.perf_counter()
    try:
        yield
    finally:
        record_stt_latency(time.perf_counter() - start, agent_id)


@contextmanager
def time_llm(agent_id: str) -> Iterator[None]:
    """Context manager to time LLM latency."""
    start = time.perf_counter()
    try:
        yield
    finally:
        record_llm_latency(time.perf_counter() - start, agent_id)


@contextmanager
def time_tts(agent_id: str) -> Iterator[None]:
    """Context manager to time TTS latency."""
    start = time.perf_counter()
    try:
        yield
    finally:
        record_tts_latency(time.perf_counter() - start, agent_id)
