"""Abstract interface and factory for inference providers.

This module defines the common interface for all inference providers
(OpenAI, Ollama, llama.cpp, etc.) and provides a factory function
to create the appropriate provider based on environment configuration.
"""

import abc
import logging
import os
import uuid
from abc import ABC
from typing import TypedDict

from kairix_core.util.utils import get_or_raise

logger = logging.getLogger(__name__)


class ModelParams(TypedDict):
    """Parameters for model configuration."""
    model: str
    use_quantization: bool


class InferenceParams(TypedDict):
    """Parameters for inference request."""
    requested_tokens: int
    temperature: float
    chat_template: str
    system_instruction: str | None
    user_prompt: str | None


class InferenceProvider(ABC):
    """Abstract base class for all inference providers."""
    
    @abc.abstractmethod
    def predict(self, content: str, inference_params: InferenceParams) -> str:
        """Generate a prediction based on input content.
        
        Args:
            content: The input text to process
            inference_params: Parameters controlling the inference
            
        Returns:
            Generated text response
        """
        raise NotImplementedError()


class MockInferenceProvider(InferenceProvider):
    """Mock provider for testing that returns random UUIDs."""
    
    def predict(self, content: str, inference_params: InferenceParams) -> str:
        """Return a random UUID instead of actual inference."""
        return str(uuid.uuid4())


def get_inference_provider_for_environement(model_parameters: ModelParams) -> InferenceProvider:
    """Factory function to create inference provider based on environment.
    
    Reads KAIRIX_INFERENCE_PROVIDER environment variable to determine
    which provider to instantiate.
    
    Args:
        model_parameters: Model configuration parameters
        
    Returns:
        Configured inference provider instance
        
    Raises:
        KeyError: If required environment variables are missing
    """
    provider = get_or_raise("KAIRIX_INFERENCE_PROVIDER")

    if provider == "mock":
        return MockInferenceProvider()

    api_key = os.getenv("KAIRIX_INFERENCE_API_KEY")
    from kairix_core.inference.openai import OpenAIInferenceProvider

    if provider == "openai":
        provider_instance: InferenceProvider = OpenAIInferenceProvider(model_parameters=model_parameters, api_key=api_key)
        return provider_instance

    if provider not in ["ollama"]:
        logger.warning(f"Unknown provider {provider}. Assuming Open AI compatible. Requires KAIRIX_INFERENCE_BASE_URL.")

    base_url = get_or_raise("KAIRIX_INFERENCE_BASE_URL")
    provider_instance = OpenAIInferenceProvider(model_parameters=model_parameters, base_url=base_url, api_key=api_key)
    return provider_instance
