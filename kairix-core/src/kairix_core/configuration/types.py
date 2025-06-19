from typing import Literal

from pydantic import BaseModel

ProviderName = Literal["openai" , "ollama-remote" , "ollama-local"]

class AgentConfig(BaseModel):
    name: str
    model: str
    temperature: float = 0.8
    max_tokens: int = 256


class AgentConfigurationSet(BaseModel):
    name: str
    default_provider: ProviderName
    description: str
    agent_configs: dict[str, AgentConfig]
