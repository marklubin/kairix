"""
chat_fragment.py - Wrapper for chat conversations with plain text stores.

This module provides a ChatFragment class that:
1. Stores conversations in human-readable plain text format using chatformat
2. Maintains metadata needed for tracking and stores
3. Provides conversion between formats for LLM and stores needs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
from pathlib import Path
import json

try:
    from chatformat import format_chat_prompt
except ImportError:
    # Fallback for when chatformat isn't installed yet
    format_chat_prompt = None


@dataclass
class ChatFragment:
    """
    A wrapper for chat conversations that stores content in plain text format.

    The actual conversation is stored as formatted plain text (via chatformat),
    while metadata is kept separately for database stores and tracking.
    """

    # Core conversation data
    messages: List[Dict[str, str]] = field(
        default_factory=list
    )  # chatformat style: [{'role': 'user', 'content': '...'}]

    # Metadata fields (from original Message/Conversation models)
    fragment_id: str = ""
    title: str = "untitled conversation"
    openai_conversation_id: str = ""
    create_time: datetime = field(default_factory=datetime.utcnow)
    update_time: datetime = field(default_factory=datetime.utcnow)

    # Additional metadata for messages (stored separately)
    message_metadata: List[Dict[str, Any]] = field(default_factory=list)

    def add_message(self, role: str, content: str, **metadata) -> None:
        """Add a message to the conversation."""
        # Add the core message in chatformat style
        self.messages.append({"role": role, "content": content})

        # Store any additional metadata
        meta = {"created_at": datetime.utcnow().isoformat(), **metadata}
        self.message_metadata.append(meta)
        self.update_time = datetime.utcnow()

    def to_plain_text(self, template: str = "llama-2") -> str:
        """
        Convert conversation to plain text format using chatformat.

        Args:
            template: The chat template to use (e.g., 'llama-2', 'vicuna', 'alpaca')

        Returns:
            Formatted plain text representation of the conversation
        """
        if not self.messages:
            return ""

        if format_chat_prompt is None:
            # Fallback formatting if chatformat isn't available
            lines = []
            for msg in self.messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                lines.append(f"{role}: {content}")
            return "\n\n".join(lines)

        # Use chatformat for proper formatting
        prompt, _ = format_chat_prompt(template, self.messages)
        return prompt

    def save_to_file(self, filepath: Path, include_metadata: bool = True) -> None:
        """
        Save conversation to a plain text file.

        Args:
            filepath: Path to save the file
            include_metadata: Whether to include metadata as a header comment
        """
        content = []

        # Add metadata as a comment header if requested
        if include_metadata:
            meta = {
                "fragment_id": self.fragment_id,
                "title": self.title,
                "openai_conversation_id": self.openai_conversation_id,
                "create_time": self.create_time.isoformat(),
                "update_time": self.update_time.isoformat(),
                "message_count": len(self.messages),
            }
            content.append(
                f"# Conversation Metadata\n# {json.dumps(meta, indent=2).replace(chr(10), chr(10) + '# ')}\n"
            )

        # Add the plain text conversation
        content.append(self.to_plain_text())

        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text("\n".join(content))

    @classmethod
    def from_file(cls, filepath: Path) -> ChatFragment:
        """
        Load a conversation from a plain text file.

        This is a basic implementation that parses simple role: content format.
        For production use, this would need more sophisticated parsing.
        """
        content = filepath.read_text()

        # Extract metadata if present
        metadata = {}
        lines = content.split("\n")

        # Parse metadata from comment header
        if lines and lines[0].startswith("# Conversation Metadata"):
            meta_lines = []
            i = 1
            while i < len(lines) and lines[i].startswith("#"):
                meta_lines.append(lines[i][2:])  # Remove '# ' prefix
                i += 1

            try:
                metadata = json.loads("\n".join(meta_lines))
            except json.JSONDecodeError:
                pass

        # Create fragment with metadata
        fragment = cls(
            fragment_id=metadata.get("fragment_id", ""),
            title=metadata.get("title", "untitled conversation"),
            openai_conversation_id=metadata.get("openai_conversation_id", ""),
        )

        # Parse messages (basic implementation)
        # In production, this would need to handle the specific template format
        current_role = None
        current_content = []

        for line in lines:
            if line.startswith("#") or not line.strip():
                continue

            # Simple parsing for "role: content" format
            if ": " in line and line.split(": ")[0] in ["system", "user", "assistant"]:
                # Save previous message if exists
                if current_role and current_content:
                    fragment.add_message(current_role, "\n".join(current_content))

                # Start new message
                parts = line.split(": ", 1)
                current_role = parts[0]
                current_content = [parts[1]] if len(parts) > 1 else []
            else:
                # Continue current message
                if current_content is not None:
                    current_content.append(line)

        # Don't forget the last message
        if current_role and current_content:
            fragment.add_message(current_role, "\n".join(current_content))

        return fragment

    def to_llm_messages(self) -> List[Dict[str, str]]:
        """
        Get messages in format ready for LLM consumption.
        This is just the messages list in chatformat style.
        """
        return self.messages

    def to_storage_format(self) -> Dict[str, Any]:
        """
        Convert to format suitable for database stores (Neo4j, etc).
        Includes all metadata and structured data.
        """
        return {
            "fragment_id": self.fragment_id,
            "title": self.title,
            "openai_conversation_id": self.openai_conversation_id,
            "create_time": self.create_time.isoformat(),
            "update_time": self.update_time.isoformat(),
            "messages": [
                {
                    **msg,
                    "metadata": self.message_metadata[i]
                    if i < len(self.message_metadata)
                    else {},
                }
                for i, msg in enumerate(self.messages)
            ],
            "plain_text": self.to_plain_text(),
        }
