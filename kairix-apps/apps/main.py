
import logging

from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.neo4j import Neo4jRuntime
from kairix_core.types.cognition import Stimulus, StimulusType
from rich import pretty
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from kairix_apps.engine import KairixEngine

neo4j  = Neo4jRuntime()
agent_runtime =AgentRuntime()
logger = logging.getLogger()

logging.getLogger("kairix_engine").setLevel(logging.DEBUG)
logging.getLogger("cognition_engine").setLevel(logging.DEBUG)


pretty.install()

console = Console()

# Create layout with 50/50 split
layout = Layout()
layout.split_row(Layout(name="left", ratio=1), Layout(name="right", ratio=1))

# Initialize panels
chat_history = []
layout["left"].update(Panel(Text(""), title="Chat", border_style="cyan"))
layout["right"].update(
    Panel(Text(""), title="Streaming Response", border_style="green")
)

# Log initialization to file instead of console
logger.info("Initializing.....")

persona = KairixEngine.conversational_persona_for_environment()
logger.info("Beginning Chat Loop.")


async def main_loop():
    # Use Live for the entire session
    with Live(layout, console=console, refresh_per_second=5, screen=True) as live:
        while True:
            # Update left panel with current chat history
            chat_text = "\n".join(chat_history)
            layout["left"].update(
                Panel(Text(chat_text), title="Chat", border_style="cyan")
            )
            live.update(layout)

            # Get user input - this will appear at the bottom
            live.stop()
            user_input = console.input("\nΩß∫>\t")
            live.start()

            # Add user input to history
            chat_history.append(f"User: {user_input}")

            # Update left panel with new input
            chat_text = "\n".join(chat_history)
            layout["left"].update(
                Panel(Text(chat_text), title="Chat", border_style="cyan")
            )

            # Clear right panel for new response
            layout["right"].update(
                Panel(Text(""), title="Streaming", border_style="green")
            )

            i = 0
            async for partial in persona.react(
                Stimulus(content=user_input, type=StimulusType.user_message)
            ):
                layout["right"].update(
                    Panel(Text(partial), title="Streaming", border_style="green")
                )
                live.update(layout)
                i += 1

            # Add response to chat history
            chat_history.append(f"AI: {partial}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main_loop())
