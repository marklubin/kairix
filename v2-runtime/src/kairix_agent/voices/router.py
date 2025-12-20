"""FastAPI router for voice management endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from kairix_agent.server.voice.pipeline_manager import voice_pipeline_manager
from kairix_agent.voices import service
from kairix_agent.voices.schemas import (
    AgentVoiceSettingsResponse,
    SetAgentVoiceRequest,
    VoiceCreate,
    VoiceResponse,
    VoiceUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voices", tags=["voices"])


# --- Voice CRUD ---


@router.get("", response_model=list[VoiceResponse])
async def list_voices() -> list[VoiceResponse]:
    """List all available voices."""
    voices = await service.list_voices()
    return [VoiceResponse.model_validate(v) for v in voices]


@router.get("/{voice_id}", response_model=VoiceResponse)
async def get_voice(voice_id: str) -> VoiceResponse:
    """Get a voice by ID."""
    voice = await service.get_voice(voice_id)
    if voice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice not found")
    return VoiceResponse.model_validate(voice)


@router.post("", response_model=VoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_voice(body: VoiceCreate) -> VoiceResponse:
    """Create a new voice."""
    voice = await service.create_voice(
        name=body.name,
        provider_voice_id=body.provider_voice_id,
        provider=body.provider,
        description=body.description,
    )
    return VoiceResponse.model_validate(voice)


@router.patch("/{voice_id}", response_model=VoiceResponse)
async def update_voice(voice_id: str, body: VoiceUpdate) -> VoiceResponse:
    """Update a voice."""
    voice = await service.update_voice(
        voice_id,
        name=body.name,
        provider_voice_id=body.provider_voice_id,
        description=body.description,
    )
    if voice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice not found")
    return VoiceResponse.model_validate(voice)


@router.delete("/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice(voice_id: str) -> None:
    """Delete a voice."""
    deleted = await service.delete_voice(voice_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice not found")


# --- Agent Voice Settings ---


@router.get("/agents/{agent_id}", response_model=AgentVoiceSettingsResponse)
async def get_agent_voice(agent_id: str) -> AgentVoiceSettingsResponse:
    """Get the voice configured for an agent."""
    voice = await service.get_agent_voice(agent_id)
    return AgentVoiceSettingsResponse(
        agent_id=agent_id,
        voice=VoiceResponse.model_validate(voice) if voice else None,
    )


@router.put("/agents/{agent_id}")
async def set_agent_voice(agent_id: str, body: SetAgentVoiceRequest) -> dict[str, Any]:
    """Set the voice for an agent and update active pipelines."""
    # Verify voice exists
    voice = await service.get_voice(body.voice_id)
    if voice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice not found")

    # Persist to database
    await service.set_agent_voice(agent_id, body.voice_id)

    # Update active pipelines
    updated_count = await voice_pipeline_manager.update_voice(
        agent_id, voice.provider_voice_id
    )

    logger.info(
        "Set voice %s for agent %s, updated %d active pipelines",
        voice.name,
        agent_id,
        updated_count,
    )

    return {
        "agent_id": agent_id,
        "voice_id": body.voice_id,
        "active_pipelines_updated": updated_count,
    }
