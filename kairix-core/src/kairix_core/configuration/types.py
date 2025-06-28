"""Configuration type definitions for Kairix agents and providers.

This module defines the core configuration data models used throughout the system
for configuring AI agents and their inference providers.
"""

from typing import Literal

from pydantic import BaseModel

# Supported inference provider backends
ProviderName = Literal["openai" , "ollama-remote" , "ollama-local","llama-cpp"]

class AgentConfig(BaseModel):
    """Configuration for an individual AI agent.
    
    Attributes:
        name: Unique identifier for the agent
        model: Model name/path to use for inference
        temperature: Sampling temperature (0.0-2.0), higher = more creative
        max_tokens: Maximum tokens to generate in responses
    """
    name: str
    model: str
    temperature: float = 0.8
    max_tokens: int = 256


class AgentConfigurationSet(BaseModel):
    """A collection of agent configurations with a default provider.
    
    This groups related agents together under a common configuration set,
    allowing for easy switching between different environments (e.g., local vs cloud).
    
    Attributes:
        name: Unique identifier for this configuration set
        default_provider: Default inference provider for all agents in this set
        description: Human-readable description of this configuration set
        agent_configs: Mapping of agent names to their configurations
    """
    name: str
    default_provider: ProviderName
    description: str
    agent_configs: dict[str, AgentConfig]
