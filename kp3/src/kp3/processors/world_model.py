"""World model extraction processor using DeepSeek.

Makes 3 parallel LLM calls to update human/persona/world blocks.
Each call sees all 3 previous states but only updates its own block.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import ExtractionPrompt, Passage
from kp3.processors.base import Processor, ProcessorGroup, ProcessorResult
from kp3.providers.deepseek import DeepSeekClient, DeepSeekError, InferenceMetadata
from kp3.schemas.world_model import (
    HumanBlock,
    PersonaBlock,
    WorldBlock,
    WorldModelState,
)
from kp3.services.derivations import create_derivations
from kp3.services.passages import create_passage
from kp3.services.prompts import get_active_prompt
from kp3.services.refs import get_ref_passage, set_ref

logger = logging.getLogger(__name__)


@dataclass
class WorldModelConfig:
    """Configuration for world model processor."""

    # LLM settings
    llm_model: str = "deepseek-chat"
    max_tokens: int = 4096
    temperature: float = 0.7

    # Refs to use for state
    human_ref: str = "world/human/HEAD"
    persona_ref: str = "world/persona/HEAD"
    world_ref: str = "world/world/HEAD"

    # Prompt names (3 separate prompts)
    human_prompt_name: str = "world_model_human"
    persona_prompt_name: str = "world_model_persona"
    world_prompt_name: str = "world_model_world"

    # Whether to update refs after creating passages
    update_refs: bool = True

    # Whether to fire hooks on ref updates
    fire_hooks: bool = True


class WorldModelProcessor(Processor[WorldModelConfig]):
    """Processor that extracts world model state from passages.

    This processor implements a fold semantic - each passage is processed
    with the previous state as context, producing an updated state.

    Makes 3 PARALLEL LLM calls:
    - Each call sees all 3 previous states (human, persona, world)
    - Each call only updates its own block

    Unlike other processors, this one manages its own DB operations:
    - Loads previous state from refs
    - Creates 3 state passages (human, persona, world)
    - Updates refs to point to new passages
    """

    def __init__(
        self,
        session: AsyncSession,
        client: DeepSeekClient | None = None,
    ) -> None:
        """Initialize the processor.

        Args:
            session: Database session for DB operations
            client: DeepSeek client (created if not provided)
        """
        self.session = session
        self._client = client or DeepSeekClient()

    async def process(
        self,
        group: ProcessorGroup,
        config: WorldModelConfig,
    ) -> ProcessorResult:
        """Process a passage to extract world model state.

        This processor expects single-passage groups (fold semantic).

        Returns:
            ProcessorResult with action="create" containing metadata about
            the created passages, or action="pass" if processing failed.
        """
        if not group.passages:
            logger.warning("Empty group, skipping")
            return ProcessorResult(action="pass")

        if len(group.passages) > 1:
            logger.warning(
                "WorldModelProcessor expects single-passage groups, got %d",
                len(group.passages),
            )

        input_passage = group.passages[0]
        logger.info("Processing passage %s for world model extraction", input_passage.id)

        try:
            # 1. Load previous state from refs
            previous_state, prior_passage_ids = await self._load_previous_state(config)
            logger.debug("Loaded previous state with %d prior passages", len(prior_passage_ids))

            # 2. Load prompts from DB (all 3)
            prompts = await self._load_prompts(config)
            if not prompts:
                return ProcessorResult(action="pass")

            # 3. Make 3 PARALLEL LLM calls
            new_state, metadata_list = await self._extract_world_model_parallel(
                passage=input_passage,
                previous_state=previous_state,
                prompts=prompts,
                config=config,
            )
            logger.info(
                "Extracted new state with versions: human=%d, persona=%d, world=%d",
                new_state.human.version,
                new_state.persona.version,
                new_state.world.version,
            )

            # 4. Create state passages with derivations
            source_ids = [input_passage.id, *prior_passage_ids]
            created_ids = await self._create_state_passages(
                new_state=new_state,
                source_ids=source_ids,
                input_passage_id=input_passage.id,
                prompts=prompts,
                metadata_list=metadata_list,
                config=config,
            )

            # 5. Update refs if configured
            if config.update_refs:
                await self._update_refs(created_ids, config)
                logger.info("Updated refs to point to new state passages")

            return ProcessorResult(
                action="create",
                content=json.dumps(
                    {
                        "human_id": str(created_ids["human"]),
                        "persona_id": str(created_ids["persona"]),
                        "world_id": str(created_ids["world"]),
                    }
                ),
                metadata={
                    "human_version": new_state.human.version,
                    "persona_version": new_state.persona.version,
                    "world_version": new_state.world.version,
                    "llm_model": config.llm_model,
                    "llm_provider": "deepseek",
                },
            )

        except DeepSeekError as e:
            logger.exception("DeepSeek API error: %s", e)
            return ProcessorResult(action="pass")
        except ValidationError as e:
            logger.exception("Failed to validate LLM response: %s", e)
            return ProcessorResult(action="pass")
        except Exception as e:
            logger.exception("Unexpected error in world model extraction: %s", e)
            return ProcessorResult(action="pass")

    async def _load_previous_state(
        self,
        config: WorldModelConfig,
    ) -> tuple[WorldModelState, list[UUID]]:
        """Load previous state from refs.

        Returns:
            Tuple of (previous_state, list of prior passage IDs)
        """
        prior_ids: list[UUID] = []
        blocks: dict[str, Any] = {}

        for block_type, ref_name in [
            ("human", config.human_ref),
            ("persona", config.persona_ref),
            ("world", config.world_ref),
        ]:
            passage = await get_ref_passage(self.session, ref_name)
            if passage:
                prior_ids.append(passage.id)
                try:
                    blocks[block_type] = json.loads(passage.content)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse %s block content", block_type)
                    blocks[block_type] = {}
            else:
                blocks[block_type] = {}

        # Build state from loaded blocks (with defaults for missing fields)
        try:
            state = WorldModelState(
                human=blocks.get("human", {}),
                persona=blocks.get("persona", {}),
                world=blocks.get("world", {}),
            )
        except ValidationError:
            # If validation fails, return empty state
            state = WorldModelState.empty()

        return state, prior_ids

    async def _load_prompts(self, config: WorldModelConfig) -> dict[str, ExtractionPrompt] | None:
        """Load all 3 prompts from DB.

        Returns:
            Dict mapping block type to prompt, or None if any missing
        """
        prompts: dict[str, ExtractionPrompt] = {}

        for block_type, prompt_name in [
            ("human", config.human_prompt_name),
            ("persona", config.persona_prompt_name),
            ("world", config.world_prompt_name),
        ]:
            prompt = await get_active_prompt(self.session, prompt_name)
            if not prompt:
                logger.error("No active prompt found for '%s'", prompt_name)
                return None
            prompts[block_type] = prompt

        return prompts

    async def _extract_world_model_parallel(
        self,
        passage: Passage,
        previous_state: WorldModelState,
        prompts: dict[str, ExtractionPrompt],
        config: WorldModelConfig,
    ) -> tuple[WorldModelState, dict[str, InferenceMetadata]]:
        """Extract updated world model via 3 parallel LLM calls.

        Each call:
        - Sees ALL previous state (human, persona, world)
        - Only updates its own block

        Returns:
            Tuple of (new_state, dict of metadata per block)
        """
        # Calculate next versions (we control versioning, not the LLM)
        next_versions = {
            "human": previous_state.human.version + 1,
            "persona": previous_state.persona.version + 1,
            "world": previous_state.world.version + 1,
        }

        # Prepare full previous state JSON for all calls
        full_previous_state = previous_state.model_dump_json(indent=2)

        # Create tasks for parallel execution
        async def extract_block(
            block_type: str,
        ) -> tuple[str, dict[str, Any], InferenceMetadata]:
            prompt = prompts[block_type]

            # Build user prompt with full state and version hint
            user_prompt = prompt.user_prompt_template.format(
                passage=passage.content,
                previous_state=full_previous_state,
                field_descriptions=json.dumps(prompt.field_descriptions, indent=2),
            )
            # Replace version placeholder with actual next version
            user_prompt = user_prompt.replace("<provided_version>", str(next_versions[block_type]))

            response, metadata = await self._client.complete_json(
                system_prompt=prompt.system_prompt,
                user_prompt=user_prompt,
                model=config.llm_model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
            )

            # Force correct version (don't trust LLM)
            response["version"] = next_versions[block_type]

            return block_type, response, metadata

        # Run all 3 extractions in parallel
        results = await asyncio.gather(
            extract_block("human"),
            extract_block("persona"),
            extract_block("world"),
        )

        # Build new state from results
        blocks: dict[str, Any] = {}
        metadata_dict: dict[str, InferenceMetadata] = {}

        for block_type, response, metadata in results:
            blocks[block_type] = response
            metadata_dict[block_type] = metadata

        # Validate and create state
        new_state = WorldModelState(
            human=HumanBlock.model_validate(blocks["human"]),
            persona=PersonaBlock.model_validate(blocks["persona"]),
            world=WorldBlock.model_validate(blocks["world"]),
        )

        return new_state, metadata_dict

    async def _create_state_passages(
        self,
        new_state: WorldModelState,
        source_ids: list[UUID],
        input_passage_id: UUID,
        prompts: dict[str, ExtractionPrompt],
        metadata_list: dict[str, InferenceMetadata],
        config: WorldModelConfig,
    ) -> dict[str, UUID]:
        """Create state passages for each block.

        Returns:
            Dict mapping block type to created passage ID
        """
        created_ids: dict[str, UUID] = {}

        for block_type in ["human", "persona", "world"]:
            block = new_state.get_block(block_type)
            content = block.model_dump_json(indent=2)
            prompt = prompts[block_type]
            metadata = metadata_list[block_type]

            passage = await create_passage(
                self.session,
                content=content,
                passage_type=f"state:{block_type}",
                metadata={
                    "version": block.version,
                    "source_passage_id": str(input_passage_id),
                    "prompt_id": str(prompt.id),
                    "prompt_version": prompt.version,
                    "llm_provider": "deepseek",
                    "llm_model": config.llm_model,
                    "prompt_tokens": metadata.prompt_tokens,
                    "completion_tokens": metadata.completion_tokens,
                },
            )

            # Create derivation links
            await create_derivations(
                self.session,
                derived_passage_id=passage.id,
                source_passage_ids=source_ids,
                processing_run_id=None,  # Will be set by run service if available
            )

            created_ids[block_type] = passage.id
            logger.debug("Created %s passage: %s", block_type, passage.id)

        return created_ids

    async def _update_refs(
        self,
        created_ids: dict[str, UUID],
        config: WorldModelConfig,
    ) -> None:
        """Update refs to point to new state passages."""
        ref_mapping = {
            "human": config.human_ref,
            "persona": config.persona_ref,
            "world": config.world_ref,
        }

        for block_type, passage_id in created_ids.items():
            ref_name = ref_mapping[block_type]
            await set_ref(
                self.session,
                ref_name,
                passage_id,
                fire_hooks=config.fire_hooks,
            )

    @classmethod
    def parse_config(cls, raw: dict[str, Any]) -> WorldModelConfig:
        """Parse raw config dict into WorldModelConfig."""
        return WorldModelConfig(
            llm_model=raw.get("llm_model", "deepseek-chat"),
            max_tokens=raw.get("max_tokens", 4096),
            temperature=raw.get("temperature", 0.7),
            human_ref=raw.get("human_ref", "world/human/HEAD"),
            persona_ref=raw.get("persona_ref", "world/persona/HEAD"),
            world_ref=raw.get("world_ref", "world/world/HEAD"),
            human_prompt_name=raw.get("human_prompt_name", "world_model_human"),
            persona_prompt_name=raw.get("persona_prompt_name", "world_model_persona"),
            world_prompt_name=raw.get("world_prompt_name", "world_model_world"),
            update_refs=raw.get("update_refs", True),
            fire_hooks=raw.get("fire_hooks", True),
        )

    @property
    def processor_type(self) -> str:
        return "world_model"
