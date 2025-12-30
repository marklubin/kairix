"""Tests for retry configuration module."""

import pytest

from kairix_agent.worker.retry import (
    LLM_RETRY_CONFIG,
    QUICK_RETRY_CONFIG,
    RetryConfig,
)


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_retry_config_creation(self) -> None:
        """RetryConfig can be created with expected values."""
        config = RetryConfig(
            retries=3,
            retry_delay=5.0,
            retry_backoff=2.0,
        )
        assert config.retries == 3
        assert config.retry_delay == 5.0
        assert config.retry_backoff == 2.0

    def test_max_delay_calculation(self) -> None:
        """max_delay property calculates correctly."""
        config = RetryConfig(
            retries=3,
            retry_delay=10.0,
            retry_backoff=2.0,
        )
        # 10 * 2^2 = 40 (for 3rd retry which is index 2)
        assert config.max_delay == 40.0

    def test_max_delay_with_no_backoff(self) -> None:
        """max_delay with backoff=1.0 stays constant."""
        config = RetryConfig(
            retries=5,
            retry_delay=10.0,
            retry_backoff=1.0,
        )
        # 10 * 1^4 = 10
        assert config.max_delay == 10.0

    def test_total_max_time_calculation(self) -> None:
        """total_max_time property calculates sum of all delays."""
        config = RetryConfig(
            retries=3,
            retry_delay=10.0,
            retry_backoff=2.0,
        )
        # 10 + 20 + 40 = 70
        assert config.total_max_time == 70.0

    def test_total_max_time_zero_retries(self) -> None:
        """total_max_time returns 0 when no retries."""
        config = RetryConfig(
            retries=0,
            retry_delay=10.0,
            retry_backoff=2.0,
        )
        assert config.total_max_time == 0.0


class TestPresetConfigs:
    """Tests for preset retry configurations."""

    def test_llm_retry_config_values(self) -> None:
        """LLM_RETRY_CONFIG has expected values."""
        assert LLM_RETRY_CONFIG.retries == 5
        assert LLM_RETRY_CONFIG.retry_delay == 10.0
        assert LLM_RETRY_CONFIG.retry_backoff == 2.0

    def test_quick_retry_config_values(self) -> None:
        """QUICK_RETRY_CONFIG has expected values."""
        assert QUICK_RETRY_CONFIG.retries == 3
        assert QUICK_RETRY_CONFIG.retry_delay == 2.0
        assert QUICK_RETRY_CONFIG.retry_backoff == 2.0

    def test_llm_config_total_time(self) -> None:
        """LLM_RETRY_CONFIG total time is reasonable (~5 minutes)."""
        # 10 + 20 + 40 + 80 + 160 = 310 seconds
        assert LLM_RETRY_CONFIG.total_max_time == 310.0

    def test_configs_are_frozen(self) -> None:
        """Preset configs are immutable (frozen dataclass)."""
        try:
            LLM_RETRY_CONFIG.retries = 10  # type: ignore[misc]
            pytest.fail("Should have raised FrozenInstanceError")
        except AttributeError:
            pass  # Expected
