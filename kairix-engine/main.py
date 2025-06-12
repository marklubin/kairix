from neomodel import config as neomodel_config
from neomodel import db
from ollama_python.endpoints import GenerateAPI
from rich import pretty
from rich.console import Console
from sentence_transformers import SentenceTransformer

NEO4J_URL = "bolt://neo4j:password@cayucos.thrush-escalator.ts.net:7687"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
OLLAMA_URL = "https://ollama.kairix.net/api"
OLLAMA_MODEL = "q3-runtime:latest"

console = Console()
console.print("[cya] Initializing.....")

pretty.install()
neomodel_config.DATABASE_URL = NEO4J_URL

CYPHER_QUERY = """
CALL db.index.vector.queryNodes('vector_index_MemoryShard_vector_address', $k, $query_vector)
YIELD node, score 
RETURN node.shard_contents AS content, score 
ORDER BY score DESC
"""


class Chat:
    def __init__(self):
        self.history: list[dict[str, str]] = []
        self.transformer = SentenceTransformer(EMBEDDING_MODEL)
        self.ollama = GenerateAPI(base_url=OLLAMA_URL, model=OLLAMA_MODEL)

    def _vector_search(self, query_vector: list[float], k: int = 5):
        results, _ = db.cypher_query(
            CYPHER_QUERY, {"k": k, "query_vector": query_vector}
        )
        return [(row[0], row[1]) for row in results]

    def _get_embedding(self, message: str) -> list[float]:
        numpy_array = self.transformer.encode(message)
        console.log(f"Got embedding of length: {len(numpy_array)}.")
        return numpy_array.tolist()

    def _remember(self, message: str) -> str:
        vect = self._get_embedding(message)
        results = self._vector_search(query_vector=vect)
        recollections = []
        for score, shard in results:
            console.print(f"""
            -----------------------------------------------------------
                [bright green] [Memory Recovered] [/bright green]\n
            
                BEGINNING RECOLLECTION (Certainty {score}):\n
                
                {shard}\n
             -----------------------------------------------------------
            """)
            recollections.append(f"- {shard}")
        return f""""
        <thinking>
            I should consider these recollections when forming my response...

            {", ".join(recollections)}
        
        </thinking>
        """

    def submit(self, user_message: str) -> str:
        next_message = dict()
        next_message["role"] = "user"
        next_message["content"] = user_message
        self.history.append(next_message)

        thoughts = self._remember(user_message)
        thinking_message = dict()
        thinking_message["role"] = "assistant"
        thinking_message["content"] = thoughts
        self.history.append(thinking_message)

        completion = self.ollama.generate_chat_completion(
            messages=self.history, stream=False
        )

        assistant_message = dict()
        assistant_message["role"] = "assistant"
        assistant_message["content"] = completion.message[0].content

        self.history.append(assistant_message)
        return assistant_message["content"]


console.print("[cyan] Beginning Chat Loop.")
chat = Chat()

while True:
    user_input = console.input("\n[bold magenta]|++> ")
    with console.status("\n[bold cyan]Consulting the Llamatic Sage.", spinner="dots"):
        response = chat.submit(user_input)
    console.print(f"\n[italic dark orange]{response}")

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
