"""
OpenAI-compatible LLM provider that wraps the existing OpenAILLM.
"""

from typing import Any, Dict, Optional

from neo4j_graphrag.llm.openai_llm import OpenAILLM

from apiana.core.providers.base import LLMProvider, LLMResponse


class OpenAICompatibleProvider(LLMProvider):
    """
    Wrapper around the existing OpenAILLM to match our provider interface.
    
    This allows us to use OpenAI, Ollama, or any OpenAI-compatible API
    through the same interface as our local provider.
    """
    
    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        self.model_name = model_name
        
        # Set up the config for the underlying OpenAILLM
        config = {
            "temperature": temperature,
            **kwargs
        }
        
        if max_tokens is not None:
            config["max_tokens"] = max_tokens
        
        # Initialize the underlying OpenAILLM
        self.llm = OpenAILLM(
            model_name=model_name,
            model_params=config,
            api_key=api_key,
            base_url=base_url
        )
    
    def invoke(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None, 
        **kwargs
    ) -> LLMResponse:
        """Generate a response using the OpenAI-compatible API."""
        # Use the existing OpenAILLM invoke method
        response = self.llm.invoke(prompt, system_instruction=system_instruction)
        
        # Wrap in our standard response format
        return LLMResponse(
            content=response.content,
            model=self.model_name,
            usage=getattr(response, 'usage', None),
            metadata=getattr(response, 'metadata', None)
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        return {
            "model_name": self.model_name,
            "provider": "openai_compatible",
            "base_url": getattr(self.llm, 'base_url', None),
        }