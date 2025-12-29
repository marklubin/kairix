"""BlockManagerAgent - Generic agent that manages Letta blocks via LLM."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx

from kairix_agent.config import Config
from kairix_agent.llm.openai_client import OpenAICompatibleClient

if TYPE_CHECKING:
    from letta_client import AsyncLetta

logger = logging.getLogger(__name__)


@dataclass
class KP3StorageConfig:
    """Configuration for storing output to KP3."""

    passage_type: str = "agent_output"
    include_input_in_metadata: bool = True


@dataclass
class PromptData:
    """Prompt data loaded from KP3."""

    id: str
    name: str
    version: int
    system_prompt: str
    user_prompt_template: str
    field_descriptions: dict[str, Any]


@dataclass
class BlockManagerConfig:
    """Configuration for a BlockManagerAgent."""

    name: str  # e.g., "summarizer", "insights"
    prompt_name: str  # KP3 ExtractionPrompt name (loaded at runtime)
    target_block: str  # Block label to update (e.g., "last_session_summary")
    model: str | None = None  # LLM model to use (defaults to Config.LLM_MODEL)
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 120.0

    # Tool use configuration
    tools: list[dict[str, Any]] = field(default_factory=list)

    # KP3 output storage (None = disabled)
    kp3_storage: KP3StorageConfig | None = None


class BlockManagerAgent:
    """Generic agent that processes input and updates a Letta block via LLM."""

    def __init__(self, config: BlockManagerConfig) -> None:
        self.config = config
        self._llm_client = OpenAICompatibleClient(model=config.model)
        self._tool_handlers: dict[str, Callable[..., Awaitable[str]]] = {}

    def register_tool_handler(
        self, name: str, handler: Callable[..., Awaitable[str]]
    ) -> None:
        """Register a handler for a tool call."""
        self._tool_handlers[name] = handler

    async def _load_prompt(self) -> PromptData:
        """Load prompt from KP3 database (always loads fresh)."""
        kp3_url = Config.KP3_URL.value
        logger.info("Loading prompt: %s", self.config.prompt_name)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{kp3_url}/prompts/{self.config.prompt_name}"
            )
            response.raise_for_status()
            data = response.json()
            prompt = PromptData(
                id=data["id"],
                name=data["name"],
                version=data["version"],
                system_prompt=data["system_prompt"],
                user_prompt_template=data["user_prompt_template"],
                field_descriptions=data.get("field_descriptions", {}),
            )
            logger.info("Loaded prompt: %s v%d", prompt.name, prompt.version)

        return prompt

    async def run(
        self,
        input_text: str,
        agent_id: str,
        letta_client: AsyncLetta,
        *,
        metadata: dict[str, Any] | None = None,
        template_vars: dict[str, str] | None = None,
    ) -> str:
        """Process input and update the target block.

        Args:
            input_text: The text to process (transcript, conversation, etc.).
            agent_id: The Letta agent ID to update.
            letta_client: Async Letta client.
            metadata: Extra metadata for KP3 storage (session_id, period_start, etc.).
            template_vars: Variables for user_prompt_template substitution.

        Returns:
            The generated text that was written to the block.
        """
        # Load prompt from KP3 (always fresh)
        prompt = await self._load_prompt()

        # Format user prompt with template variables
        vars_to_use = template_vars or {"transcript": input_text, "conversation": input_text}
        user_prompt = prompt.user_prompt_template.format(**vars_to_use)

        logger.info(
            "Running BlockManagerAgent %s: prompt=%s, target_block=%s",
            self.config.name,
            self.config.prompt_name,
            self.config.target_block,
        )

        # Call LLM with tools (handles tool call loop internally)
        result = await self._llm_client.generate(
            system_prompt=prompt.system_prompt,
            user_prompt=user_prompt,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            timeout=self.config.timeout,
            tools=self.config.tools if self.config.tools else None,
            tool_handlers=self._tool_handlers if self._tool_handlers else None,
        )

        logger.info(
            "BlockManagerAgent %s generated %d chars", self.config.name, len(result)
        )

        # Update the target block on the conversational agent
        await letta_client.agents.blocks.update(
            agent_id=agent_id,
            block_label=self.config.target_block,
            value=result,
        )
        logger.info("Updated block %s on agent %s", self.config.target_block, agent_id)

        # Optionally store output to KP3
        if self.config.kp3_storage is not None:
            await self._store_to_kp3(result, input_text, agent_id, metadata)

        return result

    async def _store_to_kp3(
        self,
        output: str,
        input_text: str,
        agent_id: str,
        extra_metadata: dict[str, Any] | None,
    ) -> None:
        """Store output to KP3 as a passage."""
        if self.config.kp3_storage is None:
            return

        kp3_url = Config.KP3_URL.value

        meta: dict[str, Any] = {
            "agent_id": agent_id,
            "agent_name": self.config.name,
        }
        if self.config.kp3_storage.include_input_in_metadata:
            meta["input_text"] = input_text[:1000]  # Truncate for metadata

        # Build payload - extract period fields from metadata for temporal indexing
        payload: dict[str, Any] = {
            "content": output,
            "passage_type": self.config.kp3_storage.passage_type,
            "metadata": meta,
        }

        # Pass period_start/period_end as passage fields (not just metadata)
        if extra_metadata:
            extra_copy = dict(extra_metadata)
            if "period_start" in extra_copy:
                payload["period_start"] = extra_copy.pop("period_start")
            if "period_end" in extra_copy:
                payload["period_end"] = extra_copy.pop("period_end")
            meta.update(extra_copy)

        logger.info(
            "Storing output to KP3: type=%s, len=%d",
            self.config.kp3_storage.passage_type,
            len(output),
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{kp3_url}/passages", json=payload)
            response.raise_for_status()
            data = response.json()
            logger.info("Stored passage: %s", data.get("id", "unknown"))
