"""Pydantic schemas for unified agent configuration."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BlockSchema(BaseModel):
    """Schema for a single memory block definition."""

    label: str = Field(..., description="Block label (e.g., 'persona', 'human')")
    description: str = Field(..., description="Block description")
    limit: int = Field(default=5000, description="Character limit for block content")
    kp3_ref_suffix: str | None = Field(
        default=None,
        description="KP3 ref suffix (e.g., 'persona/HEAD'). Full ref is {kp3_ref_prefix}/{suffix}",
    )
    initial_value: str | None = Field(
        default=None,
        description="Initial value for block when creating new agent",
    )

    model_config = ConfigDict(extra="forbid")


class AgentBase(BaseModel):
    """Base schema with common agent fields."""

    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    system_prompt: str

    # Primary LLM Config
    inference_model: str = Field(
        ...,
        description="LLM model in provider/model format (e.g., 'openai/Qwen2.5-7B-Instruct-AWQ')",
    )
    inference_provider_url: str | None = Field(
        default=None,
        description="Custom OpenAI-compatible URL for inference (e.g., 'http://vllm:8000/v1')",
    )
    embedding_model: str = "openai/text-embedding-3-small"
    context_window: int = 25000
    max_tokens: int = 4096
    enable_reasoner: bool = True
    max_reasoning_tokens: int | None = 1024

    # Background LLM Config
    background_llm_model: str = "deepseek-chat"
    background_llm_url: str = "https://api.deepseek.com"

    # Block Schema
    block_schema: list[BlockSchema] = Field(default_factory=list)

    # Tools
    tools: list[str] = Field(default_factory=list)
    include_base_tools: bool = True

    # Voice
    voice_id: str | None = None

    # KP3 Integration
    kp3_ref_prefix: str | None = Field(
        default=None,
        description="Prefix for KP3 refs (e.g., 'corindel' -> refs 'corindel/persona/HEAD')",
    )
    kp3_hooks_enabled: bool = True

    model_config = ConfigDict(extra="forbid")


class AgentCreate(AgentBase):
    """Schema for creating a new agent."""


class AgentUpdate(BaseModel):
    """Schema for updating an existing agent (all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    system_prompt: str | None = None

    inference_model: str | None = None
    inference_provider_url: str | None = None
    embedding_model: str | None = None
    context_window: int | None = None
    max_tokens: int | None = None
    enable_reasoner: bool | None = None
    max_reasoning_tokens: int | None = None

    background_llm_model: str | None = None
    background_llm_url: str | None = None

    block_schema: list[BlockSchema] | None = None

    tools: list[str] | None = None
    include_base_tools: bool | None = None

    voice_id: str | None = None

    kp3_ref_prefix: str | None = None
    kp3_hooks_enabled: bool | None = None

    model_config = ConfigDict(extra="forbid")


class AgentRead(AgentBase):
    """Schema for reading agent data (includes DB-generated fields)."""

    id: str

    # Letta Sync State (read-only)
    letta_agent_id: str | None = None
    letta_archive_id: str | None = None
    letta_synced_at: datetime | None = None
    letta_sync_hash: str | None = None

    # Timestamps
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AgentSyncResult(BaseModel):
    """Result of syncing an agent to Letta."""

    agent_id: str
    agent_name: str
    letta_agent_id: str
    synced: bool = Field(..., description="True if sync was performed, False if skipped")
    message: str


class AgentListItem(BaseModel):
    """Lightweight schema for listing agents."""

    id: str
    name: str
    description: str | None
    letta_agent_id: str | None
    letta_synced_at: datetime | None
    voice_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
