"""
Validation processor component for filtering ChatFragments.
"""

import time
from typing import List

from apiana.core.components.common import ComponentResult
from apiana.core.components.transform.base import Transform
from apiana.types.chat_fragment import ChatFragment


class ValidationTransform(Transform):
    """Processor that validates ChatFragments and filters out invalid ones."""
    
    # Type specifications
    input_types = [List[ChatFragment], ChatFragment]  # List of fragments or single fragment
    output_types = [List[ChatFragment]]  # Always outputs list of valid fragments

    def __init__(self, name: str = "validator", config: dict = None):
        super().__init__(name, config)

    def validate_input(self, input_data) -> List[str]:
        """Validate that input is a list of ChatFragments."""
        errors = []

        if isinstance(input_data, list):
            if not all(isinstance(item, ChatFragment) for item in input_data):
                errors.append("All items in list must be ChatFragment instances")
        elif not isinstance(input_data, ChatFragment):
            errors.append("Input must be a ChatFragment or list of ChatFragments")

        return errors

    def transform(self, data) -> ComponentResult:
        """Transform by validating and filtering fragments."""
        start_time = time.time()

        fragments = data if isinstance(data, list) else [data]
        valid_fragments = []
        warnings = []

        min_messages = self.config.get("min_messages", 1)
        max_messages = self.config.get("max_messages", None)
        require_title = self.config.get("require_title", False)

        for i, fragment in enumerate(fragments):
            issues = []

            # Check message count
            message_count = len(fragment.messages)
            if message_count < min_messages:
                issues.append(f"Too few messages: {message_count} < {min_messages}")

            if max_messages and message_count > max_messages:
                issues.append(f"Too many messages: {message_count} > {max_messages}")

            # Check for title if required
            if require_title and not fragment.title.strip():
                issues.append("Missing title")

            # Check for empty messages
            empty_messages = sum(
                1 for msg in fragment.messages if not msg.get("content", "").strip()
            )
            if empty_messages > 0:
                issues.append(f"{empty_messages} empty messages")

            if issues:
                warning = f"Fragment {i} ({fragment.title}): {'; '.join(issues)}"
                warnings.append(warning)
            else:
                valid_fragments.append(fragment)

        execution_time = (time.time() - start_time) * 1000

        metadata = {
            "input_fragments": len(fragments),
            "valid_fragments": len(valid_fragments),
            "filtered_out": len(fragments) - len(valid_fragments),
        }

        return ComponentResult(
            data=valid_fragments,
            metadata=metadata,
            warnings=warnings,
            execution_time_ms=execution_time,
        )
