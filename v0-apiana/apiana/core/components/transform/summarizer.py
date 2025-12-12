"""
Summarizer processor component for generating conversation summaries.
"""

import time
from typing import List

from apiana.core.components.common import ComponentResult
from apiana.core.components.transform.base import Transform
from apiana.types.chat_fragment import ChatFragment


class SummarizerTransform(Transform):
    """Processor that summarizes conversations using an LLM provider."""
    
    # Type specifications
    input_types = [List[ChatFragment], ChatFragment]  # List of fragments or single fragment
    output_types = [List[dict]]  # List of dictionaries with summary data

    def __init__(self, name: str = "summarizer", config: dict = None):
        super().__init__(name, config)
        self.llm_provider = None  # Will be injected

    def set_llm_provider(self, provider):
        """Inject the LLM provider to use for summarization."""
        self.llm_provider = provider

    def validate_input(self, input_data) -> List[str]:
        """Validate that input is a list of ChatFragments."""
        errors = []

        if self.llm_provider is None:
            errors.append("LLM provider not set. Call set_llm_provider() first.")

        if isinstance(input_data, list):
            if not all(isinstance(item, ChatFragment) for item in input_data):
                errors.append("All items in list must be ChatFragment instances")
        elif not isinstance(input_data, ChatFragment):
            errors.append("Input must be a ChatFragment or list of ChatFragments")

        return errors

    def transform(self, data) -> ComponentResult:
        """Transform fragments by generating summaries."""
        start_time = time.time()

        fragments = data if isinstance(data, list) else [data]
        summaries = []
        errors = []

        system_prompt = self.config.get(
            "system_prompt",
            "Summarize this conversation in a concise, informative way.",
        )
        user_template = self.config.get(
            "user_template", "Please summarize this conversation:\n\n{conversation}"
        )

        for i, fragment in enumerate(fragments):
            try:
                # Get conversation as plain text
                conversation_text = fragment.to_plain_text()

                # Format the prompt
                user_prompt = user_template.format(conversation=conversation_text)

                # Call LLM
                response = self.llm_provider.invoke(
                    user_prompt, system_instruction=system_prompt
                )
                summary = (
                    response.content if hasattr(response, "content") else str(response)
                )

                summaries.append(
                    {
                        "fragment_id": fragment.fragment_id,
                        "title": fragment.title,
                        "summary": summary,
                        "original_messages": len(fragment.messages),
                    }
                )

            except Exception as e:
                error_msg = f"Failed to summarize fragment {i}: {e}"
                errors.append(error_msg)
                summaries.append(
                    {
                        "fragment_id": fragment.fragment_id,
                        "title": fragment.title,
                        "summary": None,
                        "error": error_msg,
                        "original_messages": len(fragment.messages),
                    }
                )

        execution_time = (time.time() - start_time) * 1000

        metadata = {
            "fragments_processed": len(fragments),
            "summaries_generated": len([s for s in summaries if s.get("summary")]),
            "failures": len([s for s in summaries if s.get("error")]),
        }

        return ComponentResult(
            data=summaries,
            metadata=metadata,
            errors=errors,
            execution_time_ms=execution_time,
        )
