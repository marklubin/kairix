"""Utility functions for configuration management.

Provides helper functions for working with agent configurations and providers.
"""

from kairix_core.configuration.types import ProviderName


def model_for_provider(provider_name: ProviderName, model: str) -> str:
    """Format model name based on provider requirements.
    
    Different providers expect model names in different formats:
    - OpenAI: Just the model name (e.g., "gpt-4")
    - Others: Provider prefix + model (e.g., "ollama-local/llama2")
    
    Args:
        provider_name: The inference provider being used
        model: Base model name
        
    Returns:
        Properly formatted model string for the provider
    """
    if provider_name == "openai":
        return model
    return f"{provider_name}/{model}"
