"""CRUD service for unified agent configuration."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from kairix_agent.agents.models import Agent
from kairix_agent.agents.schemas import AgentCreate, AgentRead, AgentUpdate, BlockSchema

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgentService:
    """Service for managing unified agent configuration."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, agent_id: str) -> Agent | None:
        """Get an agent by its UUID."""
        result = await self.session.execute(select(Agent).where(Agent.id == agent_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Agent | None:
        """Get an agent by name (case-insensitive)."""
        result = await self.session.execute(
            select(Agent).where(Agent.name.ilike(name))
        )
        return result.scalar_one_or_none()

    async def get_by_letta_id(self, letta_agent_id: str) -> Agent | None:
        """Get an agent by its Letta agent ID."""
        result = await self.session.execute(
            select(Agent).where(Agent.letta_agent_id == letta_agent_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Agent]:
        """List all agents."""
        result = await self.session.execute(
            select(Agent).order_by(Agent.name)
        )
        return list(result.scalars().all())

    async def create(self, data: AgentCreate) -> Agent:
        """Create a new agent."""
        agent = Agent(
            name=data.name,
            description=data.description,
            system_prompt=data.system_prompt,
            inference_model=data.inference_model,
            inference_provider_url=data.inference_provider_url,
            embedding_model=data.embedding_model,
            context_window=data.context_window,
            max_tokens=data.max_tokens,
            enable_reasoner=data.enable_reasoner,
            max_reasoning_tokens=data.max_reasoning_tokens,
            background_llm_model=data.background_llm_model,
            background_llm_url=data.background_llm_url,
            block_schema=[b.model_dump() for b in data.block_schema],
            tools=data.tools,
            include_base_tools=data.include_base_tools,
            voice_id=data.voice_id,
            kp3_ref_prefix=data.kp3_ref_prefix,
            kp3_hooks_enabled=data.kp3_hooks_enabled,
        )
        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def update(self, agent: Agent, data: AgentUpdate) -> Agent:
        """Update an existing agent."""
        update_data = data.model_dump(exclude_unset=True)

        # Convert block_schema if present
        if "block_schema" in update_data and update_data["block_schema"] is not None:
            update_data["block_schema"] = [
                b.model_dump() if isinstance(b, BlockSchema) else b
                for b in update_data["block_schema"]
            ]

        for key, value in update_data.items():
            setattr(agent, key, value)

        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def delete(self, agent: Agent) -> None:
        """Delete an agent."""
        await self.session.delete(agent)
        await self.session.commit()

    def compute_sync_hash(self, agent: Agent) -> str:
        """Compute a hash of agent config for change detection.

        This hash is used to determine if an agent needs to be synced to Letta.
        It includes all config that affects the Letta agent.
        """
        config_dict = {
            "name": agent.name,
            "system_prompt": agent.system_prompt,
            "inference_model": agent.inference_model,
            "inference_provider_url": agent.inference_provider_url,
            "embedding_model": agent.embedding_model,
            "context_window": agent.context_window,
            "max_tokens": agent.max_tokens,
            "enable_reasoner": agent.enable_reasoner,
            "max_reasoning_tokens": agent.max_reasoning_tokens,
            "block_schema": agent.block_schema,
            "tools": agent.tools,
            "include_base_tools": agent.include_base_tools,
        }
        config_json = json.dumps(config_dict, sort_keys=True)
        return hashlib.sha256(config_json.encode()).hexdigest()[:16]

    def needs_sync(self, agent: Agent) -> bool:
        """Check if agent needs to be synced to Letta."""
        if agent.letta_agent_id is None:
            return True
        current_hash = self.compute_sync_hash(agent)
        return agent.letta_sync_hash != current_hash

    async def mark_synced(
        self,
        agent: Agent,
        letta_agent_id: str,
        letta_archive_id: str | None = None,
    ) -> Agent:
        """Mark agent as synced to Letta."""
        agent.letta_agent_id = letta_agent_id
        agent.letta_archive_id = letta_archive_id
        agent.letta_sync_hash = self.compute_sync_hash(agent)
        agent.letta_synced_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    def get_block_schemas(self, agent: Agent) -> list[BlockSchema]:
        """Parse block_schema JSONB into BlockSchema objects."""
        return [BlockSchema.model_validate(b) for b in agent.block_schema]

    def get_kp3_ref_name(self, agent: Agent, block_label: str) -> str | None:
        """Get full KP3 ref name for a block.

        Returns None if agent has no kp3_ref_prefix or block has no kp3_ref_suffix.
        """
        if not agent.kp3_ref_prefix:
            return None

        for block in self.get_block_schemas(agent):
            if block.label == block_label and block.kp3_ref_suffix:
                return f"{agent.kp3_ref_prefix}/{block.kp3_ref_suffix}"

        return None


async def get_agent_for_letta_id(
    session: AsyncSession,
    letta_agent_id: str,
) -> AgentRead | None:
    """Helper to get agent config by Letta agent ID.

    This is useful for worker jobs that receive a Letta agent ID
    and need to look up the unified config.
    """
    service = AgentService(session)
    agent = await service.get_by_letta_id(letta_agent_id)
    if agent is None:
        return None
    return AgentRead.model_validate(agent)
