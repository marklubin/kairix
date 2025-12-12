import logging
import os

from rich.logging import RichHandler

from apiana.types.configuration import (
    Neo4jConfig,
    PromptConfig,
    ApianaRuntimeConfig,
    TextGenerationModelConfig,
    InferenceProviderConfig,
)

# Stage-based configuration dictionary
STAGE_CONFIGS = {
    "openai": ApianaRuntimeConfig(
        environment_stage="default",
        enable_remote_debug=False,
        log_level=logging.INFO,
        neo4j=Neo4jConfig(),
        summarizer=TextGenerationModelConfig(
            prompt_config=PromptConfig(
                "summarizer",
                "prompts/self-reflective-system-message.txt",
                "prompts/self-reflective-prompt-template.txt",
            ),
            inference_provider_config=InferenceProviderConfig(),
            model_name="gpt-4o",
        ),
        embedding_model_name="nomic-ai/nomic-embed-text-v1",
    ),
    "default": ApianaRuntimeConfig(
        environment_stage="default",
        enable_remote_debug=False,
        log_level=logging.INFO,
        neo4j=Neo4jConfig(),
        summarizer=TextGenerationModelConfig(
            prompt_config=PromptConfig(
                "summarizer",
                "prompts/self-reflective-system-message.txt",
                "prompts/self-reflective-prompt-template.txt",
            ),
            inference_provider_config=InferenceProviderConfig(
                base_url="https://ollama.kairix.net/v1"
            ),
            model_name="hf.co/bartowski/huihui-ai_Mistral-Small-24B-Instruct-2501-abliterated-GGUF:Q4_K_M",
        ),
        embedding_model_name="nomic-ai/nomic-embed-text-v1",
    ),
    "unit-test": ApianaRuntimeConfig(
        environment_stage="unit-test",
        enable_remote_debug=False,
        log_level=logging.WARNING,  # Less verbose for tests
        neo4j=Neo4jConfig(
            host="localhost",
            port=7688,  # Different port to avoid conflicts
            database="test",
            username="neo4j",
            password="test-password",
        ),
        summarizer=TextGenerationModelConfig(
            prompt_config=PromptConfig(
                "test-summarizer",
                "tests/fixtures/test-system-prompt.txt",
                "tests/fixtures/test-user-prompt.txt",
            ),
            inference_provider_config=InferenceProviderConfig(
                base_url="http://mock-llm-service"
            ),
            model_name="mock-model",
            temperature=0.0,  # Deterministic for tests
            max_tokens=50,  # Small for fast tests
        ),
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",  # Smaller, faster model for tests
    ),
}

# Get the current stage from environment variable
current_stage = os.environ.get("APIANA_ENV_STAGE", "default")

# Select the appropriate config
runtime_config = STAGE_CONFIGS.get(current_stage, STAGE_CONFIGS["default"])


FORMAT = "%(message)s"
logging.basicConfig(
    level=runtime_config.log_level,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler()],
)

if runtime_config.enable_remote_debug:
    import pdb

    pdb.set_trace()
