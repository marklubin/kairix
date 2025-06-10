import abc
import logging
import os
import uuid
from abc import ABC
from typing import TypedDict

from kairix_core.util.environment import get_or_raise

logger = logging.getLogger(__name__)


class ModelParams(TypedDict):
    model: str
    use_quantization: bool


class InferenceParams(TypedDict):
    requested_tokens: int
    temperature: float
    chat_template: str
    system_instruction: str | None
    user_prompt: str | None


class InferenceProvider(ABC):
    @abc.abstractmethod
    def predict(self, content: str, inference_params: InferenceParams):
        raise NotImplementedError()


class MockInferenceProvider(InferenceProvider):
    def predict(self, content: str, inference_params: InferenceParams):
        return str(uuid.uuid4())


def get_inference_provider_for_environement(model_parameters: ModelParams):
    provider = get_or_raise("KAIRIX_INFERENCE_PROVIDER")

    if provider == "mock":
        return MockInferenceProvider()

    if provider == "vllm":
        from kairix_core.inference.vllm import VLLMInferenceProvider  # noqa conditional import for mac compatibility

        return VLLMInferenceProvider(model_parameters=model_parameters)

    api_key = os.getenv("KAIRIX_INFERENCE_API_KEY")
    from kairix_core.inference.openai import OpenAIInferenceProvider

    if provider == "openai":
        return OpenAIInferenceProvider(
            model_parameters=model_parameters, api_key=api_key
        )

    if provider not in ["ollama"]:
        logger.warning(
            f"Unknown provider {provider}. Assuming Open AI compatible. "
            f"Requires KAIRIX_INFERENCE_BASE_URL."
        )

    base_url = get_or_raise("KAIRIX_INFERENCE_BASE_URL")
    return OpenAIInferenceProvider(
        model_parameters=model_parameters, base_url=base_url, api_key=api_key
    )
