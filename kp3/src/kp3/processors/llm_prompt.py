"""LLM prompt processor using Anthropic Claude."""

from dataclasses import dataclass
from typing import Any

import anthropic

from kp3.config import get_settings
from kp3.processors.base import Processor, ProcessorGroup, ProcessorResult


@dataclass
class LLMPromptConfig:
    """Configuration for LLM prompt processor."""

    prompt_template: str = "Summarize the following:\n\n{passages}"
    model: str | None = None  # None = use default from settings
    system_prompt: str | None = None
    max_tokens: int = 4096


class LLMPromptProcessor(Processor[LLMPromptConfig]):
    """Processor that uses Claude to generate new passages from groups."""

    def __init__(self, client: anthropic.AsyncAnthropic | None = None) -> None:
        settings = get_settings()
        self._client = client or anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._default_model = settings.anthropic_model

    async def process(
        self,
        group: ProcessorGroup,
        config: LLMPromptConfig,
    ) -> ProcessorResult:
        """Process passages with LLM to generate new content."""
        if not group.passages:
            return ProcessorResult(action="pass")

        model = config.model or self._default_model

        # Format passages for prompt
        passages_text = "\n\n---\n\n".join(
            f"[{i + 1}] {p.content}" for i, p in enumerate(group.passages)
        )

        # Build prompt from template - explicit args override group_metadata
        format_args = {
            **group.group_metadata,
            "passages": passages_text,
            "count": len(group.passages),
            "group_key": group.group_key,
        }
        prompt = config.prompt_template.format(**format_args)

        # Call Claude
        messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": config.max_tokens,
            "messages": messages,
        }
        if config.system_prompt:
            kwargs["system"] = config.system_prompt

        response = await self._client.messages.create(**kwargs)

        # Extract text from response
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        if not content.strip():
            return ProcessorResult(action="pass")

        return ProcessorResult(
            action="create",
            content=content,
            metadata={
                "model": model,
                "group_key": group.group_key,
                "source_count": len(group.passages),
                **group.group_metadata,
            },
            period_start=group.group_metadata.get("period_start"),
            period_end=group.group_metadata.get("period_end"),
        )

    @classmethod
    def parse_config(cls, raw: dict) -> LLMPromptConfig:
        """Parse raw config dict into LLMPromptConfig."""
        return LLMPromptConfig(
            prompt_template=raw.get("prompt_template", "Summarize the following:\n\n{passages}"),
            model=raw.get("model"),
            system_prompt=raw.get("system_prompt"),
            max_tokens=raw.get("max_tokens", 4096),
        )

    @property
    def processor_type(self) -> str:
        return "llm_prompt"
