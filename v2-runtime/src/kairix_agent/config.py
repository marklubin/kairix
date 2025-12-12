"""Centralized configuration from environment variables."""

import os
from enum import Enum


class Config(Enum):
    """Application configuration sourced from environment variables.

    Note: For background worker jobs, agent-specific config (agent_id, letta_url,
    archive_id, reflector_id) is passed explicitly to jobs via MONITORED_AGENTS.
    This allows monitoring multiple agents simultaneously.

    The LETTA_* env vars below are used by the voice server and provisioning CLI.
    """

    # Redis configuration
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Postgres configuration
    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://kairix:kairix@localhost:5432/kairix"
    )

    # Session detection settings
    SESSION_GAP_MINUTES = int(os.getenv("SESSION_GAP_MINUTES", "5"))

    # Letta configuration (for voice server and provisioning CLI)
    LETTA_BASE_URL = os.getenv("LETTA_BASE_URL", "http://localhost:9000")
    LETTA_AGENT_ID = os.getenv("LETTA_AGENT_ID", "")

    # Worker agent monitoring (comma-separated list of agent IDs)
    MONITORED_AGENT_IDS = os.getenv("MONITORED_AGENT_IDS", "")

    # External API keys (for voice pipeline)
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
