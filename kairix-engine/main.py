import logging

from dotenv import load_dotenv
from rich import pretty
from rich.console import Console
from rich.logging import RichHandler

from kairix_engine.engine import KairixEngine

if not load_dotenv():
    raise ValueError("Failed to load .env file.")

logging.basicConfig(datefmt="[%X]", handlers=[RichHandler()], force=True)

logger = logging.getLogger()
logger.setLevel(logging.WARNING)

logging.getLogger("kairix_engine").setLevel(logging.DEBUG)
logging.getLogger("cognition_engine").setLevel(logging.DEBUG)


pretty.install()

console = Console()
console.print("[cyan] Initializing.....")

chat = KairixEngine.get_chat_for_environment()
console.print("[cyan] Beginning Chat Loop.")


async def main_loop():
    while True:
        user_input = console.input("\n[bold magenta]|++> ")
        with console.status(
            "\n[bold italic green]Peering into my soul...", spinner="material"
        ):
            message = await chat.chat(user_input)
            console.print(f"[italic cyan]{message}\n")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main_loop())
