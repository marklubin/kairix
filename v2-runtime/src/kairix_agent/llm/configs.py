"""BlockManagerAgent configurations - loads prompts from KP3 database."""

from kairix_agent.llm.block_manager import BlockManagerConfig, KP3StorageConfig
from kairix_agent.llm.tools import SEARCH_KP3_TOOL

# Summarizer config - manages the last_session_summary block
# Stores output to KP3 as session_summary passages
SUMMARIZER_CONFIG = BlockManagerConfig(
    name="summarizer",
    prompt_name="block_manager_summarizer",  # Loaded from KP3 at runtime
    target_block="last_session_summary",
    max_tokens=4096,
    temperature=0.7,
    timeout=180.0,  # Longer timeout for large sessions
    tools=[],  # No tools for summarizer
    kp3_storage=KP3StorageConfig(
        passage_type="session_summary",
        include_input_in_metadata=False,  # Input is full transcript - too large
    ),
)

# Insights config - manages the background_insights block
# Has search_kp3 tool for looking up context
INSIGHTS_CONFIG = BlockManagerConfig(
    name="insights",
    prompt_name="block_manager_insights",  # Loaded from KP3 at runtime
    target_block="background_insights",
    max_tokens=1024,
    temperature=0.7,
    timeout=10.0,  # Short timeout for near-realtime context injection
    tools=[SEARCH_KP3_TOOL],  # Give insights agent the search tool
    kp3_storage=None,  # Don't store insights
)

# Step configs - update memory blocks after session summarization
# Each agent sees all 3 blocks (persona, human, world) but only updates its own
# All have search_kp3 tool to look up supporting information

PERSONA_STEP_CONFIG = BlockManagerConfig(
    name="persona_step",
    prompt_name="step_persona",  # Loaded from KP3 at runtime
    target_block="persona",
    max_tokens=2048,
    temperature=0.7,
    timeout=60.0,
    tools=[SEARCH_KP3_TOOL],  # Can search KP3 for supporting info
    kp3_storage=KP3StorageConfig(
        passage_type="step:persona",
        include_input_in_metadata=False,
    ),
)

HUMAN_STEP_CONFIG = BlockManagerConfig(
    name="human_step",
    prompt_name="step_human",  # Loaded from KP3 at runtime
    target_block="human",
    max_tokens=2048,
    temperature=0.7,
    timeout=60.0,
    tools=[SEARCH_KP3_TOOL],  # Can search KP3 for supporting info
    kp3_storage=KP3StorageConfig(
        passage_type="step:human",
        include_input_in_metadata=False,
    ),
)

WORLD_STEP_CONFIG = BlockManagerConfig(
    name="world_step",
    prompt_name="step_world",  # Loaded from KP3 at runtime
    target_block="world",
    max_tokens=4096,  # Larger for structured world data
    temperature=0.7,
    timeout=60.0,
    tools=[SEARCH_KP3_TOOL],  # Can search KP3 for supporting info
    kp3_storage=KP3StorageConfig(
        passage_type="step:world",
        include_input_in_metadata=False,
    ),
)

# =============================================================================
# Social Agent Configurations
# =============================================================================
# These configs power the social agents feature - evaluation, drafting,
# episodic memory, and entity model management.

# Evaluate a social post for engagement worthiness
# Returns structured decision (engage/skip) with rationale
SOCIAL_EVALUATE_CONFIG = BlockManagerConfig(
    name="social_evaluate",
    prompt_name="social_evaluate",  # Loaded from KP3 at runtime
    target_block=None,  # No block update - just returns decision
    max_tokens=1024,
    temperature=0.3,  # Low temperature for consistent decisions
    timeout=30.0,
    tools=[SEARCH_KP3_TOOL],  # Can search for entity models, past interactions
    kp3_storage=None,  # Don't store evaluations
)

# Draft a response to a social post
# Output goes to approval queue, not a memory block
SOCIAL_DRAFT_CONFIG = BlockManagerConfig(
    name="social_draft",
    prompt_name="social_draft",  # Loaded from KP3 at runtime
    target_block=None,  # No block update - draft goes to approval queue
    max_tokens=2048,
    temperature=0.7,  # Normal creativity for natural responses
    timeout=60.0,
    tools=[SEARCH_KP3_TOOL],  # Can search for entity models, context
    kp3_storage=None,  # Don't store drafts (they go to approval queue)
)

# Summarize a social interaction episode
# Creates concise summary for episodic memory
SOCIAL_EPISODE_SUMMARIZE_CONFIG = BlockManagerConfig(
    name="social_episode_summarize",
    prompt_name="social_episode_summarize",  # Loaded from KP3 at runtime
    target_block=None,  # No block update - stores to KP3 directly
    max_tokens=1024,
    temperature=0.5,
    timeout=30.0,
    tools=[],  # No tools needed for summarization
    kp3_storage=KP3StorageConfig(
        passage_type="social_episode_summary",
        include_input_in_metadata=False,
    ),
)

# Reflect on a social interaction's significance
# May update social_persona block if something meaningful was learned
SOCIAL_REFLECT_CONFIG = BlockManagerConfig(
    name="social_reflect",
    prompt_name="social_reflect",  # Loaded from KP3 at runtime
    target_block="social_persona",  # May update social persona
    max_tokens=2048,
    temperature=0.7,
    timeout=60.0,
    tools=[SEARCH_KP3_TOOL],  # Can search for relevant history
    kp3_storage=KP3StorageConfig(
        passage_type="social_reflection",
        include_input_in_metadata=False,
    ),
)

# Update or create an entity model after interaction
# Stores mental model of people/agents interacted with
ENTITY_MODEL_UPDATE_CONFIG = BlockManagerConfig(
    name="entity_model_update",
    prompt_name="entity_model_update",  # Loaded from KP3 at runtime
    target_block=None,  # No block update - stores to KP3 directly
    max_tokens=2048,
    temperature=0.7,
    timeout=60.0,
    tools=[SEARCH_KP3_TOOL],  # Can search for existing entity model
    kp3_storage=KP3StorageConfig(
        passage_type="entity_model",
        include_input_in_metadata=False,
    ),
)
