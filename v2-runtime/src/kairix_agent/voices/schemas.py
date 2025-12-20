"""Pydantic schemas for voice API."""

from datetime import datetime

from pydantic import BaseModel


class VoiceCreate(BaseModel):
    """Schema for creating a voice."""

    name: str
    provider_voice_id: str
    provider: str = "cartesia"
    description: str | None = None


class VoiceUpdate(BaseModel):
    """Schema for updating a voice."""

    name: str | None = None
    provider_voice_id: str | None = None
    description: str | None = None


class VoiceResponse(BaseModel):
    """Schema for voice response."""

    id: str
    name: str
    provider_voice_id: str
    provider: str
    description: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class AgentVoiceSettingsResponse(BaseModel):
    """Schema for agent voice settings response."""

    agent_id: str
    voice: VoiceResponse | None

    model_config = {"from_attributes": True}


class SetAgentVoiceRequest(BaseModel):
    """Request to set an agent's voice."""

    voice_id: str
