import time
from collections.abc import Generator

from neomodel import config as neomodel_config
from neomodel import db
from ollama import ChatResponse, Client, Message
from rich import pretty
from rich.console import Console
from sentence_transformers import SentenceTransformer

NEO4J_URL = "bolt://neo4j:password@cayucos.thrush-escalator.ts.net:7687"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

OLLAMA_MODEL = "q3tiny"

console = Console()
console.print("[cyan] Initializing.....")

pretty.install()
neomodel_config.DATABASE_URL = NEO4J_URL

CYPHER_QUERY = """
CALL db.index.vector.queryNodes('vector_index_MemoryShard_vector_address',\
    $k, $query_vector)
YIELD node, score 
RETURN node.shard_contents AS content, score 
ORDER BY score DESC
"""


def stream_print(text: str, delay: float = 0.001) -> None:
    for c in text:
        console.print(c, end="")
        time.sleep(delay)
    console.print("")


class Chat:
    def __init__(self):
        self.history: list[Message] = []
        self.transformer = SentenceTransformer(EMBEDDING_MODEL)
        self.ollama = Client(host="https://ollama.kairix.net")

    def _vector_search(self, query_vector: list[float], k: int = 2):
        results, _ = db.cypher_query(
            CYPHER_QUERY, {"k": k, "query_vector": query_vector}
        )
        return [
            (shard_with_score[0][9:], shard_with_score[1])
            for shard_with_score in results
        ]

    def _get_embedding(self, message: str) -> list[float]:
        numpy_array = self.transformer.encode(message)
        console.log(f"Got embedding of length: {len(numpy_array)}.")
        return numpy_array.tolist()

    def _remember(self, message: str) -> str:
        vect = self._get_embedding(message)
        results = self._vector_search(query_vector=vect)
        recollections = ""
        for shard, score in results:
            # console.print("\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            # console.print("[green] [Memory Recovered] [/green]")
            # console.print(f"BEGINNING RECOLLECTION (Certainty [red]{score}[/red])...")
            # console.print(shard)
            # console.print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n")
            recollections += shard
        return f""""
        <RECOLLECTIONS>{recollections}</RECOLLECTIONS>
        """

    def submit(self, content: str) -> Message:
        recollections = self._remember(content)
        user_message = Message(role="user", content=content + recollections)

        self.history.append(user_message)

        # console.print(user_message.content)

        response = self.ollama.chat(
            model=OLLAMA_MODEL, messages=self.history, stream=False
        )
        assert type(response) is ChatResponse
        assistant_message = response.message
        assert response.message is not None

        self.history.append(assistant_message)

        return assistant_message

    def stream(self, content: str) -> Generator:
        Message(role="user", content=content)
        pass


console.print("[cyan] Beginning Chat Loop.")
chat = Chat()

while True:
    user_input = console.input("\n[bold magenta]|++> ")
    # full_response = ""
    with console.status(
        "\n[bold italic green]Consulting the Llamatic Sage.", spinner="material"
    ):
        message = chat.submit(user_input)
        console.print(f"[italic cyan]{message.thinking}\n")
        console.print(f"[white]{message.content}\n")
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
