"""OpenTelemetry metrics for worker jobs.

Provides instrumentation for tracking job execution, block updates,
tool usage, and search results.
"""

from __future__ import annotations

import functools
import logging
import os
import time
from typing import TYPE_CHECKING, ParamSpec, TypeVar

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

# Type vars for the decorator
P = ParamSpec("P")
T = TypeVar("T")

# Global meter (lazy initialized)
_meter: metrics.Meter | None = None
_initialized: bool = False


def _is_metrics_enabled() -> bool:
    """Check if metrics export is enabled via environment."""
    return os.environ.get("ENABLE_METRICS", "").lower() in ("1", "true", "yes")


def init_metrics() -> None:
    """Initialize the metrics provider with OTLP exporter.

    Call this once at worker startup. Safe to call multiple times.
    """
    global _meter, _initialized  # noqa: PLW0603

    if _initialized:
        return

    _initialized = True

    if not _is_metrics_enabled():
        logger.info("Metrics disabled (ENABLE_METRICS not set)")
        _meter = metrics.get_meter("kairix-worker")
        return

    try:
        # Import OTLP exporter only when needed (may not be installed)
        import base64  # noqa: PLC0415

        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (  # noqa: PLC0415
            OTLPMetricExporter,
        )
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader  # noqa: PLC0415

        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:5081")

        # OpenObserve requires Basic auth for OTLP ingestion
        # Format: "org_name:api_token" base64 encoded
        otel_user = os.environ.get("OTEL_EXPORTER_OTLP_USER", "admin@kairix.local")
        otel_pass = os.environ.get("OTEL_EXPORTER_OTLP_PASSWORD", "kairix123")
        auth_string = f"{otel_user}:{otel_pass}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        headers = {"Authorization": f"Basic {auth_bytes}"}

        exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True, headers=headers)
        reader = PeriodicExportingMetricReader(exporter, export_interval_millis=30000)
        provider = MeterProvider(
            resource=Resource.create({"service.name": "kairix-worker"}),
            metric_readers=[reader],
        )
        metrics.set_meter_provider(provider)
        _meter = metrics.get_meter("kairix-worker")

        logger.info("Metrics initialized, exporting to %s", endpoint)

    except ImportError:
        logger.warning("OTLP metric exporter not available, metrics disabled")
        _meter = metrics.get_meter("kairix-worker")
    except Exception:
        logger.exception("Failed to initialize metrics")
        _meter = metrics.get_meter("kairix-worker")


def get_meter() -> metrics.Meter:
    """Get the metrics meter, initializing if needed."""
    if _meter is None:
        init_metrics()

    # After init, _meter should never be None
    assert _meter is not None  # noqa: S101
    return _meter


# ============================================================================
# Lazy instrument accessors (created on first use)
# ============================================================================

_job_counter: metrics.Counter | None = None
_job_duration: metrics.Histogram | None = None
_block_counter: metrics.Counter | None = None
_tool_counter: metrics.Counter | None = None
_kp3_histogram: metrics.Histogram | None = None


def _get_job_counter() -> metrics.Counter:
    global _job_counter  # noqa: PLW0603
    if _job_counter is None:
        _job_counter = get_meter().create_counter(
            "job_runs_total",
            description="Total job execution count",
        )
    return _job_counter


def _get_job_duration() -> metrics.Histogram:
    global _job_duration  # noqa: PLW0603
    if _job_duration is None:
        _job_duration = get_meter().create_histogram(
            "job_duration_seconds",
            description="Job execution duration in seconds",
        )
    return _job_duration


def _get_block_counter() -> metrics.Counter:
    global _block_counter  # noqa: PLW0603
    if _block_counter is None:
        _block_counter = get_meter().create_counter(
            "block_updates_total",
            description="Block update attempts",
        )
    return _block_counter


def _get_tool_counter() -> metrics.Counter:
    global _tool_counter  # noqa: PLW0603
    if _tool_counter is None:
        _tool_counter = get_meter().create_counter(
            "tool_calls_total",
            description="Tool invocation count",
        )
    return _tool_counter


def _get_kp3_histogram() -> metrics.Histogram:
    global _kp3_histogram  # noqa: PLW0603
    if _kp3_histogram is None:
        _kp3_histogram = get_meter().create_histogram(
            "kp3_search_results",
            description="KP3 search result counts",
        )
    return _kp3_histogram


# ============================================================================
# Recording functions
# ============================================================================


def record_job_run(job_type: str, status: str, agent_id: str) -> None:
    """Record a job execution.

    Args:
        job_type: The job type (e.g., "session_boundary", "summarize").
        status: Job status ("success" or "error").
        agent_id: The agent ID.
    """
    _get_job_counter().add(1, {"job_type": job_type, "status": status, "agent_id": agent_id})


def record_job_duration(job_type: str, duration: float) -> None:
    """Record job execution duration.

    Args:
        job_type: The job type.
        duration: Duration in seconds.
    """
    _get_job_duration().record(duration, {"job_type": job_type})


def record_block_update(block_type: str, *, updated: bool, agent_id: str) -> None:
    """Record a block update attempt.

    Args:
        block_type: Block label (e.g., "persona", "human", "world").
        updated: Whether the block was actually updated.
        agent_id: The agent ID.
    """
    _get_block_counter().add(
        1, {"block_type": block_type, "updated": str(updated).lower(), "agent_id": agent_id}
    )


def record_tool_call(tool_name: str, agent_id: str) -> None:
    """Record a tool invocation.

    Args:
        tool_name: Name of the tool (e.g., "search_kp3").
        agent_id: The agent ID.
    """
    _get_tool_counter().add(1, {"tool_name": tool_name, "agent_id": agent_id})


def record_kp3_results(count: int, agent_id: str) -> None:
    """Record KP3 search result count.

    Args:
        count: Number of results returned.
        agent_id: The agent ID.
    """
    _get_kp3_histogram().record(count, {"agent_id": agent_id})


# ============================================================================
# Decorator for job instrumentation
# ============================================================================


def instrument_job(
    job_type: str,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator to instrument an async job function.

    Records job_runs_total counter and job_duration_seconds histogram.

    Args:
        job_type: The job type name for metrics labels.

    Returns:
        Decorated function.
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Extract agent_id from kwargs if available
            agent_id = str(kwargs.get("agent_id", "unknown"))
            start = time.perf_counter()
            status = "success"

            try:
                return await func(*args, **kwargs)
            except Exception:
                status = "error"
                raise
            finally:
                duration = time.perf_counter() - start
                record_job_run(job_type, status, agent_id)
                record_job_duration(job_type, duration)

        return wrapper

    return decorator
