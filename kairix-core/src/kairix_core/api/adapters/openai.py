"""OpenAI API adapter for Kairix personas.

This module provides a decoupled adapter layer that translates between
OpenAI's API format and Kairix's internal persona system.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Protocol, List
import time
import uuid

# Import types from OpenAI package
from openai.types.chat import (
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionChunk,
    ChatCompletion,
)
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import Choice as ChunkChoice, ChoiceDelta
from openai.types import CompletionUsage


# Persona Protocol (what we expect from any persona implementation)
class PersonaProtocol(Protocol):
    """Protocol defining what we need from a persona."""
    
    def respond(self, message: str, context: dict) -> AsyncIterator[str]:
        """Generate streaming response to a message with context."""
        ...


# Abstract adapter interface
class PersonaAdapter(ABC):
    """Abstract adapter for converting between API formats and personas."""
    
    @abstractmethod
    def convert_messages(self, messages: List[ChatCompletionMessageParam]) -> tuple[str, dict]:
        """Convert OpenAI messages to persona input format.
        
        Returns:
            tuple of (message, context)
        """
        pass
    
    @abstractmethod
    def stream_response(
        self, 
        persona: PersonaProtocol,
        messages: List[ChatCompletionMessageParam],
        model: str,
        **kwargs
    ) -> AsyncIterator[ChatCompletionChunk]:
        """Stream responses from persona in OpenAI format."""
        pass
    
    @abstractmethod
    async def complete_response(
        self,
        persona: PersonaProtocol,
        messages: List[ChatCompletionMessageParam],
        model: str,
        **kwargs
    ) -> ChatCompletion:
        """Get complete response from persona in OpenAI format."""
        pass


class OpenAIAdapter(PersonaAdapter):
    """Concrete adapter implementation for OpenAI API compatibility."""
    
    def convert_messages(self, messages: List[ChatCompletionMessageParam]) -> tuple[str, dict]:
        """Convert OpenAI messages to persona input format."""
        if not messages:
            raise ValueError("Messages list cannot be empty")
        
        # Extract conversation history (all but last message)
        history_parts = []
        for msg in messages[:-1]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            name = msg.get("name", "")
            
            # Handle different content types
            if isinstance(content, list):
                # For multipart content, extract text
                text_parts = [part.get("text", "") for part in content if part.get("type") == "text"]
                content = " ".join(text_parts)
            elif content is None:
                content = ""
            else:
                content = str(content)
            
            role_name = name or ("User" if role == "user" else "Assistant")
            history_parts.append(f"{role_name}: {content}")
        
        # Last message is the current input
        last_msg = messages[-1]
        if last_msg.get("role") != "user":
            raise ValueError("Last message must be from user")
        
        last_content = last_msg.get("content", "")
        if isinstance(last_content, list):
            text_parts = [part.get("text", "") for part in last_content if part.get("type") == "text"]
            last_content = " ".join(text_parts)
        elif last_content is None:
            last_content = ""
        else:
            last_content = str(last_content)
        
        context = {
            "conversation_history": "\n".join(history_parts),
        }
        
        return last_content, context
    
    async def stream_response(
        self,
        persona: PersonaProtocol,
        messages: List[ChatCompletionMessageParam],
        model: str,
        **kwargs
    ) -> AsyncIterator[ChatCompletionChunk]:
        """Stream responses with delta chunks."""
        message, context = self.convert_messages(messages)
        response_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        created = int(time.time())
        
        accumulated = ""
        async for chunk in persona.respond(message, context):
            # Calculate delta (new characters only)
            if len(chunk) > len(accumulated):
                delta = chunk[len(accumulated):]
                accumulated = chunk
                
                yield ChatCompletionChunk(
                    id=response_id,
                    object="chat.completion.chunk",
                    created=created,
                    model=model,
                    choices=[ChunkChoice(
                        index=0,
                        delta=ChoiceDelta(content=delta),
                        finish_reason=None
                    )]
                )
        
        # Final chunk
        yield ChatCompletionChunk(
            id=response_id,
            object="chat.completion.chunk",
            created=created,
            model=model,
            choices=[ChunkChoice(
                index=0,
                delta=ChoiceDelta(),
                finish_reason="stop"
            )]
        )
    
    async def complete_response(
        self,
        persona: PersonaProtocol,
        messages: List[ChatCompletionMessageParam],
        model: str,
        **kwargs
    ) -> ChatCompletion:
        """Get complete response (non-streaming)."""
        message, context = self.convert_messages(messages)
        response_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        created = int(time.time())
        
        # Collect full response
        chunks = []
        async for chunk in persona.respond(message, context):
            chunks.append(chunk)
        
        full_response = chunks[-1] if chunks else ""
        
        # Count tokens (simplified - would use tiktoken in production)
        prompt_tokens = sum(len(str(m.get("content", "")).split()) for m in messages) * 2
        completion_tokens = len(full_response.split()) * 2
        
        return ChatCompletion(
            id=response_id,
            object="chat.completion",
            created=created,
            model=model,
            choices=[Choice(
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content=full_response
                ),
                finish_reason="stop"
            )],
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )


class StreamingDeltaConverter:
    """Utility for converting accumulated strings to delta chunks."""
    
    def __init__(self):
        self.accumulated = ""
    
    def get_delta(self, new_content: str) -> str:
        """Get the delta between accumulated and new content."""
        if len(new_content) > len(self.accumulated):
            delta = new_content[len(self.accumulated):]
            self.accumulated = new_content
            return delta
        return ""
    
    def reset(self):
        """Reset the accumulated content."""
        self.accumulated = ""