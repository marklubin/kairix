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
