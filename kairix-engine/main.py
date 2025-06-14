import logging

from agents import Runner
from cognition_engine.perceptor.conversation_remembering_perceptor import (
    ConversationRememberingPerceptor,
)
from rich import pretty
from rich.console import Console
from rich.logging import RichHandler

from kairix_engine.basic_chat import Chat
from kairix_engine.summary_store import SummaryStore

NEO4J_URL = "bolt://neo4j:password@cayucos.thrush-escalator.ts.net:7687"
logging.basicConfig(datefmt="[%X]", handlers=[RichHandler()], force=True)


logger = logging.getLogger()
logger.setLevel(logging.WARNING)

logging.getLogger("kairix_engine").setLevel(logging.DEBUG)
logging.getLogger("cognition_engine").setLevel(logging.DEBUG)

pretty.install()

console = Console()
console.print("[cyan] Initializing.....")

store = SummaryStore(store_url=NEO4J_URL)
perceptor = ConversationRememberingPerceptor(
    Runner(),
    memory_provider=lambda query, k: [
        content for content, score in store.search(query, k)
    ],
    k_memories=20,
)
chat = Chat(user_name="Mark", agent_name="Apiana", perceptor=perceptor)

console.print("[cyan] Beginning Chat Loop.")


async def main_loop():
    while True:
        user_input = console.input("\n[bold magenta]|++> ")
        # full_response = ""
        with console.status(
            "\n[bold italic green]Peering into my soul...", spinner="material"
        ):
            message = await chat.chat(user_input)
            console.print(f"[italic cyan]{message}\n")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main_loop())

    # for chunk in chat.submit(user_input):
    #     console.print(chunk, end="")
    #     full_response += chunk

#
# with gr.Blocks() as demo:
#     chatbot = gr.Chatbot(type="messages")
#     msg = gr.Textbox()
#     clear = gr.Button("Clear")
#
#     def user(user_message, history: list):
#         return "", history + [{"role": "user", "content": user_message}]
#
#     def bot(history: list):
#         bot_message = random.choice(["How are you?", "I love you", "I'm very hungry"])
#         history.append({"role": "assistant", "content": ""})
#         for character in bot_message:
#             history[-1]["content"] += character
#             time.sleep(0.05)
#             yield history
#
#     msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
#         bot, chatbot, chatbot
#     )
#     clear.click(lambda: None, None, chatbot, queue=False)
#
# if __name__ == "__main__":
#     demo.launch()
