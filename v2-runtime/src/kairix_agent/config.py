"""Centralized configuration from environment variables."""

import os
from enum import Enum

import dotenv

dotenv.load_dotenv()


class Config(Enum):
    """Application configuration sourced from environment variables.

    Note: For background worker jobs, agents are discovered dynamically
    from the Letta API at job execution time.

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

    # Insights job settings - only trigger if message in last N minutes
    INSIGHTS_ACTIVITY_MINUTES = int(os.getenv("INSIGHTS_ACTIVITY_MINUTES", "1"))

    # Letta configuration (for voice server and provisioning CLI)
    LETTA_BASE_URL = os.getenv("LETTA_BASE_URL", "http://localhost:9000")
    LETTA_AGENT_ID = os.getenv("LETTA_AGENT_ID", "")

    # External API keys (for voice pipeline)
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    # LLM configuration (for BlockManagerAgent - works with any OpenAI-compatible API)
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

    # KP3 service configuration
    KP3_URL = os.getenv("KP3_URL", "http://localhost:8080")

    # Social agents configuration
    # Generate key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    CREDENTIAL_ENCRYPTION_KEY = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")
