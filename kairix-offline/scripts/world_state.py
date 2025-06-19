from kairix_core.types import Summary
from agents import Agent, Runner, ModelSettings, function_tool, AgentOutputSchema

from rich.logging import RichHandler
from rich import print
import logging


logging.basicConfig(handlers=[RichHandler()])
logger = logging.getLogger(__name__)


# Global variables for schema evolution
current_world_state = dict()


schema = [
    "username",
    "assistant_namelocation",
    "time_of_day",
    "weather",
    "user_mood",
    "assistant_moodcurrent_activityuser_current_goals",
    "people_present",
    "mode_of_transportation",
    "topics_of_focus",
]


@function_tool
def delete_schema_key(key: str):
    schema.remove(key)
    if key in current_world_state:
        del current_world_state[key]


@function_tool
def add_schema_key(key: str):
    schema.append(key)


# Agent 4: Schema Lord
schema_lord_prompt = """
You are the Schema Lord. You maintain a JSON schema for representing world state.

Given:
1. New content to ingest
2. Current schema

Decide ONE of:
- Add a new field
- Remove an unused or poorly defined field 
- No change (if current schema suffices)

Only make changes for SIGNIFICANT gaps or redundancies. The schema should be minimal but sufficient.

Output your decision with clear reasoning.
"""

schema_lord = Agent(
    "schema_lord",
    instructions=schema_lord_prompt,
    tools=[add_schema_key, delete_schema_key],
    model="gpt-4o-mini",
    model_settings=ModelSettings(temperature=0.3, max_tokens=4000),
)

# Agent 5: Data Loader
data_loader_prompt = """
Given:
1. Previous world state (JSON)
2. New content to ingest
3. Current schema

You only allowed to output information inaccordance the provided schema which is a simple key-value store with no
nesting. If discover information which is not representable in the current schema then you must append a not to a 
special key in the object mapping called "BLINDSPOTS" which includes a short description of the infromation you were 
unable to include and why not for each instance this occurs.


Update the world state by:
- Preserving all existing valid data
- Adding new information from the content
- Following the schema structure exactly
- Only including information that fits the schema.


Output the complete updated world state as JSON.
"""

data_loader = Agent(
    "data_loader",
    instructions=data_loader_prompt,
    output_type=AgentOutputSchema(WorldState, strict_json_schema=False),
    model="gpt-4o-mini",
    model_settings=ModelSettings(temperature=0.2, max_tokens=8000),
)


def update_world_state(summary: Summary):
    global schema, current_world_state

    print("\n=== SCHEMA EVOLUTION ===")
    # Check if schema needs updating
    schema_input = {
        "content": summary.summary_text,
        "current_schema": schema,
        "world_state": current_world_state,
    }
    schema_update = Runner.run_sync(schema_lord, str(schema_input)).final_output
    print(f"Schema Update: {schema_update}.")

    print("\n=== WORLD STATE UPDATE ===")
    # Update world state
    data_input = {
        "previous_state": current_world_state,
        "new_content": summary.summary_text,
        "schema": schema,
    }
    world_update = Runner.run_sync(data_loader, str(data_input)).final_output
    print(f"Updated World State: {world_update}")

    current_world_state = world_update
    return world_update
