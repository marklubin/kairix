"""Request/Response models for OpenAI-compatible API."""

from typing import List, Optional, Union, Literal, Dict, Any

from pydantic import BaseModel


class Model(BaseModel):
    """Represents a model in the models list."""
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str


class ChatCompletionRequestMessage(BaseModel):
    """Message in a chat completion request."""
    role: Literal["system", "user", "assistant", "function", "tool"]
    content: Optional[Union[str, List[Dict[str, Any]]]] = None
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatCompletionRequestTool(BaseModel):
    """Tool definition in a chat completion request."""
    type: Literal["function"]
    function: Dict[str, Any]


class CreateChatCompletionRequest(BaseModel):
    """Request for creating a chat completion."""
    model: str
    messages: List[ChatCompletionRequestMessage]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    tools: Optional[List[ChatCompletionRequestTool]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, Any]] = None
    seed: Optional[int] = None