"""Configuration settings for KP3."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="KP3_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore legacy env vars (e.g., KP3_OLLAMA_*)
    )

    # Database
    database_url: str = "postgresql+asyncpg://kp3:kp3@localhost:5432/kp3"

    # OpenAI embeddings
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-large"
    openai_embedding_dim: int = 1024  # text-embedding-3-large supports 256-3072

    # Anthropic (for LLM processing)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-5-20251101"

    # DeepSeek (for world model extraction)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Query service
    query_host: str = "0.0.0.0"  # noqa: S104 - intentional bind to all interfaces
    query_port: int = 8080

    # Hybrid search RRF weights
    rrf_weight_fts: float = 1.0
    rrf_weight_semantic: float = 1.0
    rrf_weight_recency: float = 0.5


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
