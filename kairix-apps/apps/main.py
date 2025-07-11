
import logging

from kairix_core.runtime.agent import AgentRuntime
from kairix_core.types.cognition import Stimulus, StimulusType
from rich import pretty
from rich.console import Console
from rich.progress import Progress, TextColumn

from kairix_apps.engine import KairixEngine

agent_runtime = AgentRuntime()
logger = logging.getLogger()

# logging.getLogger("kairix_engine").setLevel(logging.DEBUG)
# logging.getLogger("cognition_engine").setLevel(logging.DEBUG)

pretty.install()
console = Console()


logger.info("Initializing.....")
persona = KairixEngine.conversational_persona_for_environment()
logger.info("Beginning Chat Loop.")
chat_history = []


async def main_loop():

    while True:
        # Update left panel with current chat history

        user_input = console.input("[bold purple]\nΩß∫>[/] ")

        # Add user input to history
        chat_history.append(f"User: {user_input}")

        progress = Progress(TextColumn("{task.description}"))

        task_id = progress.add_task("get_response")


        with progress as progress:
            partial = ""
            async for partial in persona.react(
                Stimulus(content=user_input, type=StimulusType.user_message)
            ):
                progress.update(task_id, description=partial)


        chat_history.append(f"Assistant: {partial}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main_loop())
