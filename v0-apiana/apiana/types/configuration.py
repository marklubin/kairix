from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional


class PromptConfig:
    def __init__(self, name, system_prompt_file, user_prompt_template_file):
        super().__init__()
        self.name = name
        with open(user_prompt_template_file, "r") as f:
            self.userprompt_template = f.read()
        with open(system_prompt_file, "r") as f:
            self.system_prompt = f.read()


@dataclass()
class InferenceProviderConfig:
    base_url: Optional[str] = None
    api_key: Optional[str] = None


@dataclass
class TextGenerationModelConfig:
    prompt_config: PromptConfig
    inference_provider_config: InferenceProviderConfig

    model_name: str = "gpt-4o"
    temperature: float = 0.5
    max_tokens: int = 256


@dataclass
class Neo4jConfig:
    username: str = "neo4j"
    password: str = "password"
    host: str = "localhost"
    port: int = 7687
    database: Optional[str] = None  # None uses default database


@dataclass
class ApianaRuntimeConfig:
    neo4j: Neo4jConfig
    summarizer: TextGenerationModelConfig
    embedding_model_name: str

    log_level: int = logging.INFO
    environment_stage: str = "local"
    enable_remote_debug: bool = False
