"""Configuration settings for KP3."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="KP3_", env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+asyncpg://kp3:kp3@localhost:5432/kp3"

    # Ollama (for embeddings)
    ollama_host: str = "http://localhost:11434"
    ollama_embedding_model: str = "qwen3-embedding:4b"
    ollama_embedding_dim: int = 1024

    # Anthropic (for LLM processing)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-5-20251101"

    # DeepSeek (for world model extraction)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Letta integration
    LETTA_SYNC_CONFIG_PATH: str = ""
    LETTA_BASE_URL: str = "http://localhost:8283"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience access for settings
class _SettingsProxy:
    """Lazy proxy for settings that loads on first access."""

    def __getattr__(self, name: str) -> str:
        return getattr(get_settings(), name)


settings = _SettingsProxy()
