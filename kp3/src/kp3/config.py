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

    # Embeddings - supports "ollama" or "vllm" backend
    embedding_backend: str = "ollama"  # "ollama" for containers, "vllm" for local GPU

    # Ollama settings (used when embedding_backend="ollama")
    ollama_host: str = "http://localhost:11434"
    ollama_embedding_model: str = "qwen3-embedding:4b"
    ollama_embedding_dim: int = 1024

    # vLLM settings (used when embedding_backend="vllm")
    vllm_embedding_model: str = "Qwen/Qwen3-Embedding-4B"
    vllm_embedding_dim: int = 1024  # MRL truncation from native 2560
    vllm_gpu_memory_utilization: float = 0.3
    vllm_enforce_eager: bool = True

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
