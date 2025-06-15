import logging

import gradio as gr
from agents import Runner
from cognition_engine.perceptor.conversation_remembering_perceptor import (
    ConversationRememberingPerceptor,
)

from kairix_engine.basic_chat import Chat
from kairix_engine.summary_store import SummaryStore

NEO4J_URL = "bolt://neo4j:password@cayucos.thrush-escalator.ts.net:7687"

# Configure logging
logging.basicConfig(level=logging.WARNING)
logging.getLogger("kairix_engine").setLevel(logging.INFO)
logging.getLogger("cognition_engine").setLevel(logging.INFO)

# Initialize components
store = SummaryStore(store_url=NEO4J_URL)
perceptor = ConversationRememberingPerceptor(
    Runner(),
    memory_provider=lambda query, k: [
        content for content, score in store.search(query, k)
    ],
    k_memories=10,
)
chat = Chat(user_name="Mark", agent_name="Apiana", perceptor=perceptor)

# Flag to track initialization
_initialized = False


async def ensure_initialized():
    """Ensure chat is initialized."""
    global _initialized
    if not _initialized:
        await chat.initialize()
        _initialized = True


async def respond(message, history):
    await ensure_initialized()
    """Stream responses from the chat engine"""
    history = history or []
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ""})
    
    full_response = ""
    
    # Use the streaming run() method
    async for chunk in chat.run(message):
        full_response += chunk
        history[-1]["content"] = full_response
        yield "", history


# Create Gradio interface with custom CSS for compact layout
with gr.Blocks(
    title="Kairix Chat",
    css="""
    .contain { max-width: 900px !important; }
    footer { display: none !important; }
    #component-0 { height: calc(100vh - 200px) !important; }
    .message-wrap { padding: 8px !important; }
    """
) as demo, gr.Column():
    chatbot = gr.Chatbot(
        height=450,
        bubble_full_width=False,
        avatar_images=(None, "🐝"),
        show_label=False,
        elem_id="component-0",
        autoscroll=True,  # Always scroll to bottom
        type="messages",  # Use openai-style format
    )
    
    with gr.Row():
        msg = gr.Textbox(
            placeholder="Message Apiana... (Enter to send, Shift+Enter for new line)",
            lines=1,
            max_lines=3,
            show_label=False,
            autofocus=True,
        )
        
        clear = gr.Button("Clear", scale=0, min_width=60)
    
    # Handle message submission with streaming
    msg.submit(respond, [msg, chatbot], [msg, chatbot])
    clear.click(lambda: (None, None), outputs=[msg, chatbot])


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )