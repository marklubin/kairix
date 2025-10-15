"""OpenAI API adapter for Kairix personas.

This module provides a decoupled adapter layer that translates between
OpenAI's API format and Kairix's internal persona system.
"""

import time
import uuid
from typing import Any, AsyncIterator, List

from openai.types import CompletionUsage
# Import types from OpenAI package
from openai.types.chat import (
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionChunk,
    ChatCompletion,
)
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import Choice as ChunkChoice, ChoiceDelta

from kairix_core.cognition import ConversationalPersona
from kairix_core.types.cognition import Stimulus, StimulusType


class OpenAIAdapter:
    """Concrete adapter implementation for OpenAI API compatibility."""


    def __init__(self, persona: ConversationalPersona):
        self.persona = persona

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
        messages: List[ChatCompletionMessageParam],
        model: str,
        **kwargs: Any
    ) -> AsyncIterator[ChatCompletionChunk]:
        """Stream responses with delta chunks."""
        message, context = self.convert_messages(messages)
        response_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        created = int(time.time())

        stimulus: Stimulus = Stimulus(message, StimulusType.user_message)

        async for accumulated, chunk in self.persona.react(stimulus):
            yield ChatCompletionChunk(
                id=response_id,
                object="chat.completion.chunk",
                created=created,
                model=model,
                choices=[ChunkChoice(
                    index=0,
                    delta=ChoiceDelta(content=chunk),
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
        messages: List[ChatCompletionMessageParam],
        model: str,
        **kwargs: Any
    ) -> ChatCompletion:
        """Get complete response (non-streaming)."""
        message, context = self.convert_messages(messages)
        response_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        created = int(time.time())

        stimulus: Stimulus = Stimulus(message, StimulusType.user_message)

        full_response = ""
        try:
            async for accumulated, chunk in self.persona.react(stimulus):
                full_response = accumulated
        except Exception as e:
            # If there's a validation error but we got a response, use it
            # This handles the openai-agents ResponseTextDeltaEvent logprobs validation issue
            if full_response:
                import logging
                logging.getLogger(__name__).warning(
                    f"Validation error during streaming, but got partial response: {e}"
                )
            else:
                raise

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
