"""Environment configuration for DeepEval metrics.

This module MUST be imported before any deepeval imports to ensure
the API keys and base URLs are configured correctly.

We create a custom model class that uses the OpenAI client directly
with DeepSeek's API endpoint.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Load .env file from kp3 root if it exists
_env_file = Path(__file__).parents[3] / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(_env_file)
    except ImportError:
        pass  # dotenv not available, rely on environment variables

# Get DeepSeek API key from multiple possible sources
_deepseek_key = (
    os.environ.get("DEEPSEEK_API_KEY")
    or os.environ.get("KP3_DEEPSEEK_API_KEY")
    or os.environ.get("OPENAI_API_KEY")
)

if not _deepseek_key:
    raise RuntimeError(
        "No DeepSeek API key found. Set DEEPSEEK_API_KEY or KP3_DEEPSEEK_API_KEY."
    )

# Also set OPENAI_API_KEY for any internal DeepEval components that need it
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = _deepseek_key

# Create the judge model using a custom class with DeepSeek configuration
if TYPE_CHECKING:
    from deepeval.models import DeepEvalBaseLLM

    JUDGE_MODEL: DeepEvalBaseLLM


def _create_judge_model() -> "DeepEvalBaseLLM":
    """Create the judge model with DeepSeek configuration."""
    from typing import Optional

    from deepeval.models import DeepEvalBaseLLM
    from openai import AsyncOpenAI, OpenAI

    class DeepSeekModel(DeepEvalBaseLLM):
        """Custom model wrapper for DeepSeek API via OpenAI-compatible endpoint."""

        def __init__(self, model_name: str = "deepseek-chat") -> None:
            self._model_name = model_name
            self._client = OpenAI(
                api_key=_deepseek_key,
                base_url="https://api.deepseek.com/v1",
            )
            self._async_client = AsyncOpenAI(
                api_key=_deepseek_key,
                base_url="https://api.deepseek.com/v1",
            )
            super().__init__(model_name)

        def load_model(self) -> Any:
            """Load the model (no-op for API models)."""
            return self._model_name

        def _build_schema_prompt(self, schema: type) -> str:
            """Build a prompt suffix instructing JSON output format."""
            json_schema = schema.model_json_schema()
            required = json_schema.get("required", [])
            properties = json_schema.get("properties", {})

            fields_desc = []
            for name, prop in properties.items():
                field_type = prop.get("type", "any")
                required_str = " (required)" if name in required else ""
                fields_desc.append(f'  - "{name}": {field_type}{required_str}')

            return (
                "\n\nRespond with a valid JSON object with the following fields:\n"
                + "\n".join(fields_desc)
                + "\n\nJSON:"
            )

        def generate(
            self, prompt: str, schema: Optional[type] = None
        ) -> tuple[str, float]:
            """Generate completion synchronously."""
            # Modify prompt to request JSON if schema provided
            if schema is not None:
                prompt = prompt + self._build_schema_prompt(schema)

            messages = [{"role": "user", "content": prompt}]

            params: dict[str, Any] = {
                "model": self._model_name,
                "messages": messages,
                "temperature": 0.0,
            }

            # DeepSeek supports json_object but not json_schema
            if schema is not None:
                params["response_format"] = {"type": "json_object"}

            response = self._client.chat.completions.create(**params)
            content = response.choices[0].message.content or ""

            # Calculate approximate cost (DeepSeek is very cheap)
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = (
                response.usage.completion_tokens if response.usage else 0
            )
            # DeepSeek pricing: ~$0.14/M input, ~$0.28/M output
            cost = (prompt_tokens * 0.14 + completion_tokens * 0.28) / 1_000_000

            return content, cost

        async def a_generate(
            self, prompt: str, schema: Optional[type] = None
        ) -> tuple[str, float]:
            """Generate completion asynchronously."""
            # Modify prompt to request JSON if schema provided
            if schema is not None:
                prompt = prompt + self._build_schema_prompt(schema)

            messages = [{"role": "user", "content": prompt}]

            # Ensure we use the correct model name - hardcode to avoid any interference
            model_name = "deepseek-chat"

            params: dict[str, Any] = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.0,
            }

            # DeepSeek supports json_object but not json_schema
            if schema is not None:
                params["response_format"] = {"type": "json_object"}

            response = await self._async_client.chat.completions.create(**params)
            content = response.choices[0].message.content or ""

            # Calculate approximate cost
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = (
                response.usage.completion_tokens if response.usage else 0
            )
            cost = (prompt_tokens * 0.14 + completion_tokens * 0.28) / 1_000_000

            return content, cost

        def get_model_name(self) -> str:
            """Return the model identifier."""
            return self._model_name

        async def a_generate_with_schema(
            self, prompt: str, schema: Optional[type] = None, **kwargs: Any
        ) -> str:
            """Override to return just the string result, not a tuple.

            DeepEval's a_generate_with_schema_and_extract expects non-native
            models to return just the result, not (result, cost) tuple.
            """
            content, _cost = await self.a_generate(prompt, schema=schema, **kwargs)
            return content

        async def a_generate_raw_response(
            self, prompt: str, **kwargs: Any
        ) -> tuple[Any, float]:
            """DeepSeek doesn't support log probs, raise to trigger fallback."""
            raise AttributeError("DeepSeek doesn't support log probabilities")

    model_name = os.environ.get("DEEPEVAL_JUDGE_MODEL", "deepseek-chat")
    return DeepSeekModel(model_name)


# Lazy initialization to avoid import-time API calls
_judge_model: "DeepEvalBaseLLM | None" = None


def get_judge_model() -> "DeepEvalBaseLLM":
    """Get the configured judge model (lazy initialization)."""
    global _judge_model
    if _judge_model is None:
        _judge_model = _create_judge_model()
    return _judge_model
