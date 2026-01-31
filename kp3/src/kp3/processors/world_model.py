"""World model extraction processor using DeepSeek.

Makes 3 parallel LLM calls to update human/persona/world blocks.
Each call sees all 3 previous states but only updates its own block.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import (
    ExtractionPrompt,
    Passage,
    ProcessingRun,
    WorldModelEntity,
    WorldModelProject,
    WorldModelTheme,
)
from kp3.processors.base import Processor, ProcessorGroup, ProcessorResult
from kp3.providers.deepseek import DeepSeekClient, DeepSeekError, InferenceMetadata
from kp3.schemas.world_model import (
    EntityEntry,
    HumanBlock,
    PersonaBlock,
    ProjectEntry,
    ThemeEntry,
    WorldBlock,
    WorldModelState,
)
from kp3.services.derivations import create_derivations
from kp3.services.passages import create_passage
from kp3.services.prompts import get_active_prompt
from kp3.services.refs import get_ref_passage, set_ref

# Maximum size for WorldBlock JSON before pruning kicks in
WORLD_BLOCK_MAX_CHARS = 5000

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

    # Agent ID for shadow table segmentation (required for shadow sync)
    agent_id: str = ""

    # Whether to sync to shadow tables
    sync_shadow_tables: bool = True


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

        processing_run: ProcessingRun | None = None
        try:
            # 0. Create processing run to track this commit
            processing_run = ProcessingRun(
                input_sql=f"passage_id={input_passage.id}",
                processor_type="world_model_commit",
                processor_config={
                    "llm_model": config.llm_model,
                    "agent_id": config.agent_id,
                    "human_ref": config.human_ref,
                    "persona_ref": config.persona_ref,
                    "world_ref": config.world_ref,
                },
                status="running",
                total_groups=1,
                started_at=datetime.now(timezone.utc),
            )
            self.session.add(processing_run)
            await self.session.flush()
            logger.debug("Created processing run %s", processing_run.id)

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

            # 3.5. Post-process world block: update tracking fields, prune if needed
            processing_time = datetime.now(timezone.utc)
            logger.info("Post-processing world block at %s", processing_time.isoformat())

            updated_world = _update_tracking_fields(
                new_state.world,
                previous_state.world,
                processing_time,
            )
            updated_world = _prune_world_block(updated_world)

            new_state = WorldModelState(
                human=new_state.human,
                persona=new_state.persona,
                world=updated_world,
            )

            # 3.6. Sync world block to shadow tables (if configured)
            if config.sync_shadow_tables:
                if config.agent_id:
                    await _sync_to_shadow_tables(
                        self.session,
                        updated_world,
                        config.agent_id,
                        processing_time,
                    )
                else:
                    logger.warning(
                        "Shadow table sync enabled but no agent_id configured, skipping"
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
                processing_run_id=processing_run.id,
            )

            # 5. Update refs if configured
            if config.update_refs:
                await self._update_refs(created_ids, config)
                logger.info("Updated refs to point to new state passages")

            # 6. Mark processing run as completed
            processing_run.status = "completed"
            processing_run.processed_groups = 1
            processing_run.output_count = 3  # human, persona, world passages
            processing_run.completed_at = datetime.now(timezone.utc)
            await self.session.flush()

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
                    "processing_run_id": str(processing_run.id),
                },
            )

        except DeepSeekError as e:
            logger.exception("DeepSeek API error: %s", e)
            if processing_run is not None:
                processing_run.status = "failed"
                processing_run.error_message = str(e)
                processing_run.completed_at = datetime.now(timezone.utc)
            return ProcessorResult(action="pass")
        except ValidationError as e:
            logger.exception("Failed to validate LLM response: %s", e)
            if processing_run is not None:
                processing_run.status = "failed"
                processing_run.error_message = str(e)
                processing_run.completed_at = datetime.now(timezone.utc)
            return ProcessorResult(action="pass")
        except Exception as e:
            logger.exception("Unexpected error in world model extraction: %s", e)
            if processing_run is not None:
                processing_run.status = "failed"
                processing_run.error_message = str(e)
                processing_run.completed_at = datetime.now(timezone.utc)
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
        processing_run_id: UUID,
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
                processing_run_id=processing_run_id,
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
            agent_id=raw.get("agent_id", ""),
            sync_shadow_tables=raw.get("sync_shadow_tables", True),
        )

    @property
    def processor_type(self) -> str:
        return "world_model"


# =============================================================================
# Post-Extraction Processing Functions
# =============================================================================


def _update_tracking_fields(
    new_world: WorldBlock,
    previous_world: WorldBlock,
    processing_time: datetime,
) -> WorldBlock:
    """Update tracking fields on world block entities.

    Only updates tracking for entities that appear in the new output.
    Entities only in previous state are considered removed by LLM (not tracked).

    Args:
        new_world: WorldBlock from LLM extraction
        previous_world: Previous WorldBlock state
        processing_time: Current processing timestamp

    Returns:
        Updated WorldBlock with tracking fields set
    """
    logger.info(
        "Updating tracking fields at %s - projects: %d, entities: %d, themes: %d",
        processing_time.isoformat(),
        len(new_world.active_projects),
        len(new_world.key_entities),
        len(new_world.recurring_themes),
    )

    # Build lookup maps from previous state
    prev_projects = {p.name: p for p in previous_world.active_projects}
    prev_entities = {e.name: e for e in previous_world.key_entities}
    prev_themes = {t.name: t for t in previous_world.recurring_themes}

    logger.debug(
        "Previous state had: projects=%d, entities=%d, themes=%d",
        len(prev_projects),
        len(prev_entities),
        len(prev_themes),
    )

    # Update projects
    updated_projects: list[ProjectEntry] = []
    new_project_count = 0
    updated_project_count = 0
    for proj in new_world.active_projects:
        if proj.name in prev_projects:
            # Existing project - increment count, update timestamp
            prev = prev_projects[proj.name]
            new_count = prev.occurrence_count + 1
            logger.debug(
                "Project '%s': updating count %d -> %d",
                proj.name,
                prev.occurrence_count,
                new_count,
            )
            updated_projects.append(
                ProjectEntry(
                    name=proj.name,
                    status=proj.status,
                    context=proj.context,
                    last_occurrence=processing_time,
                    occurrence_count=new_count,
                )
            )
            updated_project_count += 1
        else:
            # New project - initialize tracking
            logger.debug("Project '%s': new entry, initializing tracking", proj.name)
            updated_projects.append(
                ProjectEntry(
                    name=proj.name,
                    status=proj.status,
                    context=proj.context,
                    last_occurrence=processing_time,
                    occurrence_count=1,
                )
            )
            new_project_count += 1

    # Update entities
    updated_entities: list[EntityEntry] = []
    new_entity_count = 0
    updated_entity_count = 0
    for ent in new_world.key_entities:
        if ent.name in prev_entities:
            prev = prev_entities[ent.name]
            new_count = prev.occurrence_count + 1
            logger.debug(
                "Entity '%s': updating count %d -> %d",
                ent.name,
                prev.occurrence_count,
                new_count,
            )
            updated_entities.append(
                EntityEntry(
                    name=ent.name,
                    relevance=ent.relevance,
                    last_occurrence=processing_time,
                    occurrence_count=new_count,
                )
            )
            updated_entity_count += 1
        else:
            logger.debug("Entity '%s': new entry, initializing tracking", ent.name)
            updated_entities.append(
                EntityEntry(
                    name=ent.name,
                    relevance=ent.relevance,
                    last_occurrence=processing_time,
                    occurrence_count=1,
                )
            )
            new_entity_count += 1

    # Update themes
    updated_themes: list[ThemeEntry] = []
    new_theme_count = 0
    updated_theme_count = 0
    for theme in new_world.recurring_themes:
        if theme.name in prev_themes:
            prev = prev_themes[theme.name]
            new_count = prev.occurrence_count + 1
            logger.debug(
                "Theme '%s': updating count %d -> %d",
                theme.name,
                prev.occurrence_count,
                new_count,
            )
            updated_themes.append(
                ThemeEntry(
                    name=theme.name,
                    description=theme.description,
                    last_occurrence=processing_time,
                    occurrence_count=new_count,
                )
            )
            updated_theme_count += 1
        else:
            logger.debug("Theme '%s': new entry, initializing tracking", theme.name)
            updated_themes.append(
                ThemeEntry(
                    name=theme.name,
                    description=theme.description,
                    last_occurrence=processing_time,
                    occurrence_count=1,
                )
            )
            new_theme_count += 1

    logger.info(
        "Tracking update complete: projects (new=%d, updated=%d), "
        "entities (new=%d, updated=%d), themes (new=%d, updated=%d)",
        new_project_count,
        updated_project_count,
        new_entity_count,
        updated_entity_count,
        new_theme_count,
        updated_theme_count,
    )

    return WorldBlock(
        version=new_world.version,
        active_projects=updated_projects,
        key_entities=updated_entities,
        recurring_themes=updated_themes,
        key_insights=new_world.key_insights,  # Unchanged - LLM managed
    )


def _prune_world_block(world: WorldBlock, max_chars: int = WORLD_BLOCK_MAX_CHARS) -> WorldBlock:
    """Prune world block if it exceeds max character count.

    Pruning strategy:
    - Round-robin from each category (projects, entities, themes)
    - Within each category: oldest last_occurrence first
    - Tie-break by lowest occurrence_count
    - key_insights is NOT pruned (LLM managed)

    Args:
        world: WorldBlock to potentially prune
        max_chars: Maximum allowed characters for serialized JSON

    Returns:
        Pruned WorldBlock
    """
    # Check if pruning needed
    current_json = world.model_dump_json()
    initial_size = len(current_json)

    logger.info(
        "Checking WorldBlock size: %d chars (max=%d), projects=%d, entities=%d, themes=%d",
        initial_size,
        max_chars,
        len(world.active_projects),
        len(world.key_entities),
        len(world.recurring_themes),
    )

    if initial_size <= max_chars:
        logger.info("WorldBlock within size limit, no pruning needed")
        return world

    logger.warning(
        "WorldBlock exceeds limit by %d chars, starting pruning",
        initial_size - max_chars,
    )

    # Make mutable copies sorted by pruning priority (oldest, then least frequent)
    def sort_key(item: ProjectEntry | EntityEntry | ThemeEntry) -> tuple[datetime, int]:
        # Sort by oldest first, then lowest count
        ts = item.last_occurrence or datetime.min.replace(tzinfo=timezone.utc)
        return (ts, item.occurrence_count)

    projects = sorted(world.active_projects, key=sort_key)
    entities = sorted(world.key_entities, key=sort_key)
    themes = sorted(world.recurring_themes, key=sort_key)

    original_counts = (len(projects), len(entities), len(themes))
    category_names = ["projects", "entities", "themes"]

    # Round-robin pruning
    categories = [projects, entities, themes]
    category_idx = 0
    pruned_items: list[str] = []

    while True:
        # Build current state
        pruned = WorldBlock(
            version=world.version,
            active_projects=projects,
            key_entities=entities,
            recurring_themes=themes,
            key_insights=world.key_insights,
        )

        current_json = pruned.model_dump_json()
        current_size = len(current_json)

        if current_size <= max_chars:
            logger.info(
                "Pruning complete: %d chars (removed %d chars), "
                "projects: %d->%d, entities: %d->%d, themes: %d->%d",
                current_size,
                initial_size - current_size,
                original_counts[0],
                len(projects),
                original_counts[1],
                len(entities),
                original_counts[2],
                len(themes),
            )
            if pruned_items:
                logger.info("Pruned items: %s", ", ".join(pruned_items))
            return pruned

        # Find next non-empty category to prune from
        attempts = 0
        while attempts < 3:
            cat = categories[category_idx]
            if cat:
                removed = cat.pop(0)  # Remove oldest/least frequent
                item_desc = f"{category_names[category_idx]}:'{removed.name}'"
                pruned_items.append(item_desc)
                logger.debug(
                    "Pruned %s (last_occurrence=%s, count=%d), size now %d",
                    item_desc,
                    removed.last_occurrence.isoformat() if removed.last_occurrence else "never",
                    removed.occurrence_count,
                    current_size,
                )
                break
            category_idx = (category_idx + 1) % 3
            attempts += 1

        if attempts >= 3:
            # All categories empty, can't prune further
            logger.warning(
                "Cannot prune further, all categories empty. Final size: %d (still over by %d)",
                current_size,
                current_size - max_chars,
            )
            return pruned

        category_idx = (category_idx + 1) % 3


def _canonicalize_key(name: str) -> str:
    """Convert entity name to canonical key for deduplication.

    Canonical format:
    - Lowercase
    - Whitespace normalized (single spaces, trimmed)

    Args:
        name: Original entity name

    Returns:
        Canonical key string
    """
    # Normalize whitespace and lowercase
    return " ".join(name.lower().split())


async def _sync_to_shadow_tables(
    session: AsyncSession,
    world: WorldBlock,
    agent_id: str,
    processing_time: datetime,
) -> None:
    """Upsert world block entities to normalized shadow tables.

    For each project/entity/theme in world_block:
    - Upsert by (agent_id, canonical_key) unique constraint
    - Update last_occurrence and increment occurrence_count
    - No deletion - missing entities just don't get updated

    Args:
        session: Database session
        world: WorldBlock with entities to sync
        agent_id: Agent ID for segmentation
        processing_time: Current processing timestamp
    """
    logger.info(
        "Starting shadow table sync for agent '%s': %d projects, %d entities, %d themes",
        agent_id,
        len(world.active_projects),
        len(world.key_entities),
        len(world.recurring_themes),
    )

    # Sync projects
    for proj in world.active_projects:
        canonical_key = _canonicalize_key(proj.name)
        logger.debug(
            "Syncing project '%s' (canonical: '%s') to shadow table",
            proj.name,
            canonical_key,
        )
        stmt = insert(WorldModelProject).values(
            agent_id=agent_id,
            canonical_key=canonical_key,
            name=proj.name,
            status=proj.status,
            context=proj.context,
            last_occurrence=processing_time,
            occurrence_count=1,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_world_model_projects_agent_key",
            set_={
                "name": proj.name,  # Update display name in case it changed
                "status": proj.status,
                "context": proj.context,
                "last_occurrence": processing_time,
                "occurrence_count": WorldModelProject.occurrence_count + 1,
                "updated_at": processing_time,
            },
        )
        await session.execute(stmt)

    # Sync entities
    for ent in world.key_entities:
        canonical_key = _canonicalize_key(ent.name)
        logger.debug(
            "Syncing entity '%s' (canonical: '%s') to shadow table",
            ent.name,
            canonical_key,
        )
        stmt = insert(WorldModelEntity).values(
            agent_id=agent_id,
            canonical_key=canonical_key,
            name=ent.name,
            relevance=ent.relevance,
            last_occurrence=processing_time,
            occurrence_count=1,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_world_model_entities_agent_key",
            set_={
                "name": ent.name,
                "relevance": ent.relevance,
                "last_occurrence": processing_time,
                "occurrence_count": WorldModelEntity.occurrence_count + 1,
                "updated_at": processing_time,
            },
        )
        await session.execute(stmt)

    # Sync themes
    for theme in world.recurring_themes:
        canonical_key = _canonicalize_key(theme.name)
        logger.debug(
            "Syncing theme '%s' (canonical: '%s') to shadow table",
            theme.name,
            canonical_key,
        )
        stmt = insert(WorldModelTheme).values(
            agent_id=agent_id,
            canonical_key=canonical_key,
            name=theme.name,
            description=theme.description,
            last_occurrence=processing_time,
            occurrence_count=1,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_world_model_themes_agent_key",
            set_={
                "name": theme.name,
                "description": theme.description,
                "last_occurrence": processing_time,
                "occurrence_count": WorldModelTheme.occurrence_count + 1,
                "updated_at": processing_time,
            },
        )
        await session.execute(stmt)

    logger.info(
        "Shadow table sync complete for agent '%s': %d projects, %d entities, %d themes at %s",
        agent_id,
        len(world.active_projects),
        len(world.key_entities),
        len(world.recurring_themes),
        processing_time.isoformat(),
    )
