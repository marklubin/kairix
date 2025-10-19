"""Quick test to verify tools reference is appended to system prompt."""
import os

# Set up test environment
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KAIRIX_APP_ID"] = "test_tools_ref"
os.environ["KAIRIX_AGENT_CONFIGURATION_SET_KEY"] = "openai"
os.environ["KAIRIX_USER_NAME"] = "TestUser"
os.environ["KAIRIX_PERSONA_NAME"] = "TestAgent"
os.environ["KAIRIX_SUMMARIZATION_INTERVAL"] = "10"
os.environ["KAIRIX_MESSAGE_RETENTION_WINDOW"] = "20"
os.environ["KAIRIX_N_SUMMARIES_PER_MESSAGE"] = "5"
os.environ["KAIRIX_SERVER_PORT"] = "8000"

from kairix_apps.engine import KairixEngine
from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger

try:
    logger.info("Creating conversational persona...")
    persona = KairixEngine.conversational_persona_for_environment()

    # Get the agent's instructions
    agent = persona.actuating_agent
    instructions = agent.instructions

    # Check if tools reference is included
    if "Available Tools Reference" in instructions:
        logger.info("✓ Tools reference successfully appended to system prompt")

        # Verify key sections are present
        checks = [
            ("Notebook Tools", "Notebook section"),
            ("MCP (Model Context Protocol) Tools", "MCP section"),
            ("save(title: str", "save function signature"),
            ("dynamically configured", "MCP dynamic configuration explanation"),
            ("Tool Usage Philosophy", "Philosophy section"),
            ("What are MCP Tools?", "MCP explanation section"),
        ]

        for text, name in checks:
            if text in instructions:
                logger.info(f"  ✓ Found: {name}")
            else:
                logger.warning(f"  ✗ Missing: {name}")

        logger.info(f"\nTotal instruction length: {len(instructions)} characters")

    else:
        logger.error("✗ Tools reference NOT found in system prompt!")
        logger.error("This means the tools documentation is not being appended")

except Exception as e:
    logger.error(f"Error creating persona: {e}", exc_info=True)
