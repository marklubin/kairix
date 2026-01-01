"""Shared utilities for LLM module."""


def should_skip_block_update(response: str) -> bool:
    """Check if the LLM response indicates no block update is needed.

    Returns True if NO_UPDATE_NEEDED appears anywhere in the response
    (case-insensitive). This handles various formats like:
    - "NO_UPDATE_NEEDED"
    - "NO_UPDATE_NEEDED: rationale here"
    - "**NO_UPDATE_NEEDED:**" (markdown)
    - "Based on analysis... NO_UPDATE_NEEDED because..."

    Args:
        response: The LLM response text.

    Returns:
        True if update should be skipped, False if block should be updated.
    """
    return "NO_UPDATE_NEEDED" in response.upper()
