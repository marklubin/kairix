import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import gradio as gr
from kairix_core.inference.openai import OpenAIInferenceProvider
from kairix_core.inference.vllm import VLLMInferenceProvider
from kairix_core.inference_provider import InferenceProvider

from kairix_offline.ui.shared_theme import get_css, get_theme


def create_provider(provider_type: str, config: dict[str, Any]) -> InferenceProvider | None:
    """Create an inference provider based on type and configuration."""
    try:
        if provider_type == "OpenAI":
            return OpenAIInferenceProvider(
                api_key=config.get("api_key", os.getenv("OPENAI_API_KEY", "")),
                base_url=config.get("base_url"),
                model=config.get("model", "gpt-3.5-turbo")
            )
        if provider_type == "VLLM":
            return VLLMInferenceProvider(
                base_url=config.get("base_url", "http://localhost:8000"),
                model=config.get("model", ""),
                api_key=config.get("api_key")
            )
        if provider_type == "Custom OpenAI-Compatible":
            return OpenAIInferenceProvider(
                api_key=config.get("api_key", ""),
                base_url=config.get("base_url"),
                model=config.get("model", "")
            )
        return None
    except Exception as e:
        print(f"Error creating provider: {e}")
        return None


def query_provider(provider: InferenceProvider, prompt: str, params: dict[str, Any]) -> str:
    """Query a single provider and return the response."""
    try:
        if not provider:
            return "Error: Provider not configured"

        # Prepare inference parameters
        inference_params = {
            "requested_tokens": params.get("max_tokens", 1000),
            "temperature": params.get("temperature", 0.7),
            "top_p": params.get("top_p", 1.0),
            "frequency_penalty": params.get("frequency_penalty", 0.0),
            "presence_penalty": params.get("presence_penalty", 0.0),
        }

        # Add system prompt if provided
        if params.get("system_prompt"):
            inference_params["system_prompt"] = params["system_prompt"]

        # Get response
        response = provider.predict(prompt, inference_params)
        return response

    except Exception as e:
        return f"Error: {e!s}"


def process_all_providers(
    prompt: str,
    provider1_type: str, provider1_config: str, provider1_params: str,
    provider2_type: str, provider2_config: str, provider2_params: str,
    provider3_type: str, provider3_config: str, provider3_params: str,
    chat1: list[tuple[str, str]],
    chat2: list[tuple[str, str]],
    chat3: list[tuple[str, str]]
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]], str]:
    """Process the prompt through all configured providers concurrently."""

    if not prompt or not prompt.strip():
        return chat1, chat2, chat3, ""

    # Parse configurations and parameters
    configs = []
    params = []
    provider_types = [provider1_type, provider2_type, provider3_type]

    for config_str, param_str in [(provider1_config, provider1_params),
                                   (provider2_config, provider2_params),
                                   (provider3_config, provider3_params)]:
        try:
            config = json.loads(config_str) if config_str else {}
            param = json.loads(param_str) if param_str else {}
        except:
            config = {}
            param = {}
        configs.append(config)
        params.append(param)

    # Create providers
    providers = []
    for i, provider_type in enumerate(provider_types):
        if provider_type != "None":
            provider = create_provider(provider_type, configs[i])
            providers.append((i, provider, params[i]))
        else:
            providers.append((i, None, {}))

    # Update chat histories with user input
    chats = [chat1.copy(), chat2.copy(), chat3.copy()]
    for i, (_, provider, _) in enumerate(providers):
        if provider:
            chats[i].append((prompt, None))

    # Query all providers concurrently
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for i, provider, param in providers:
            if provider:
                future = executor.submit(query_provider, provider, prompt, param)
                futures.append((i, future))

        # Collect results as they complete
        for i, future in futures:
            try:
                response = future.result(timeout=60)
                chats[i][-1] = (prompt, response)
            except Exception as e:
                chats[i][-1] = (prompt, f"Error: {e!s}")

    return chats[0], chats[1], chats[2], ""


# Create the UI
with gr.Blocks(theme=get_theme(), css=get_css() + """
    .chatbot-container {
        height: 600px !important;
    }
    .provider-config {
        background-color: #f0f0f0;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
""") as llm_compare:
    gr.Markdown("# 🤖 LLM Compare Tool")
    gr.Markdown("Compare responses from up to 3 different LLM providers side by side")

    # Provider configurations
    with gr.Row():
        # Provider 1
        with gr.Column(scale=1):
            gr.Markdown("### Provider 1")
            provider1_type = gr.Dropdown(
                choices=["None", "OpenAI", "VLLM", "Custom OpenAI-Compatible"],
                value="None",
                label="Provider Type"
            )
            with gr.Accordion("Configuration", open=False):
                provider1_config = gr.Textbox(
                    label="Provider Config (JSON)",
                    placeholder='{"api_key": "sk-...", "base_url": "https://api.openai.com/v1", "model": "gpt-3.5-turbo"}',
                    lines=3
                )
                provider1_params = gr.Textbox(
                    label="Inference Parameters (JSON)",
                    placeholder='{"max_tokens": 1000, "temperature": 0.7, "top_p": 1.0, "system_prompt": "You are a helpful assistant."}',
                    lines=3
                )

        # Provider 2
        with gr.Column(scale=1):
            gr.Markdown("### Provider 2")
            provider2_type = gr.Dropdown(
                choices=["None", "OpenAI", "VLLM", "Custom OpenAI-Compatible"],
                value="None",
                label="Provider Type"
            )
            with gr.Accordion("Configuration", open=False):
                provider2_config = gr.Textbox(
                    label="Provider Config (JSON)",
                    placeholder='{"base_url": "http://localhost:8000", "model": "mistral-7b"}',
                    lines=3
                )
                provider2_params = gr.Textbox(
                    label="Inference Parameters (JSON)",
                    placeholder='{"max_tokens": 1000, "temperature": 0.7}',
                    lines=3
                )

        # Provider 3
        with gr.Column(scale=1):
            gr.Markdown("### Provider 3")
            provider3_type = gr.Dropdown(
                choices=["None", "OpenAI", "VLLM", "Custom OpenAI-Compatible"],
                value="None",
                label="Provider Type"
            )
            with gr.Accordion("Configuration", open=False):
                provider3_config = gr.Textbox(
                    label="Provider Config (JSON)",
                    placeholder='{"api_key": "...", "base_url": "https://...", "model": "..."}',
                    lines=3
                )
                provider3_params = gr.Textbox(
                    label="Inference Parameters (JSON)",
                    placeholder='{"max_tokens": 1000, "temperature": 0.7}',
                    lines=3
                )

    # Chat interfaces
    with gr.Row():
        chatbot1 = gr.Chatbot(label="Provider 1", elem_classes=["chatbot-container"])
        chatbot2 = gr.Chatbot(label="Provider 2", elem_classes=["chatbot-container"])
        chatbot3 = gr.Chatbot(label="Provider 3", elem_classes=["chatbot-container"])

    # User input
    with gr.Row():
        with gr.Column(scale=4):
            user_input = gr.Textbox(
                label="Your Message",
                placeholder="Enter your prompt here...",
                lines=3
            )
        with gr.Column(scale=1):
            submit_btn = gr.Button("🚀 Send to All", variant="primary", size="lg")
            clear_btn = gr.Button("🗑️ Clear All", variant="secondary")

    # Wire up the functionality
    submit_btn.click(
        fn=process_all_providers,
        inputs=[
            user_input,
            provider1_type, provider1_config, provider1_params,
            provider2_type, provider2_config, provider2_params,
            provider3_type, provider3_config, provider3_params,
            chatbot1, chatbot2, chatbot3
        ],
        outputs=[chatbot1, chatbot2, chatbot3, user_input]
    )

    # Clear all chats
    clear_btn.click(
        fn=lambda: ([], [], []),
        outputs=[chatbot1, chatbot2, chatbot3]
    )

    # Allow Enter key to submit
    user_input.submit(
        fn=process_all_providers,
        inputs=[
            user_input,
            provider1_type, provider1_config, provider1_params,
            provider2_type, provider2_config, provider2_params,
            provider3_type, provider3_config, provider3_params,
            chatbot1, chatbot2, chatbot3
        ],
        outputs=[chatbot1, chatbot2, chatbot3, user_input]
    )


def main():
    llm_compare.launch(server_name="0.0.0.0", server_port=7862)


if __name__ == "__main__":
    main()
