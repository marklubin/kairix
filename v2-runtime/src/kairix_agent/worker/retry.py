"""Shared retry configuration for worker jobs.

Provides consistent exponential backoff settings across all jobs.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for job retry with exponential backoff.

    Attributes:
        retries: Number of retry attempts (0 = no retries).
        retry_delay: Initial delay in seconds before first retry.
        retry_backoff: Multiplier for delay on each subsequent retry.
    """

    retries: int
    retry_delay: float
    retry_backoff: float

    @property
    def max_delay(self) -> float:
        """Calculate the maximum delay (on final retry)."""
        return self.retry_delay * (self.retry_backoff ** (self.retries - 1))

    @property
    def total_max_time(self) -> float:
        """Calculate approximate total time for all retries (sum of delays)."""
        if self.retries == 0:
            return 0.0
        # Sum of geometric series: a * (1 - r^n) / (1 - r)
        if self.retry_backoff == 1.0:
            return self.retry_delay * self.retries
        return self.retry_delay * (1 - self.retry_backoff**self.retries) / (1 - self.retry_backoff)


# Standard retry config for LLM-dependent jobs
# 5 attempts, starting at 10s delay (10, 20, 40, 80, 160s)
# Total max time: ~310 seconds (~5 minutes of retries)
LLM_RETRY_CONFIG = RetryConfig(
    retries=5,
    retry_delay=10.0,
    retry_backoff=2.0,
)

# Quick retry config for lightweight operations
# 3 attempts, starting at 2s delay (2, 4, 8s)
QUICK_RETRY_CONFIG = RetryConfig(
    retries=3,
    retry_delay=2.0,
    retry_backoff=2.0,
)
