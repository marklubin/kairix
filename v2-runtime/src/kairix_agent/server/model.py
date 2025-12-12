from typing import Literal

from pydantic import BaseModel


class InputChunk(BaseModel):
    type: Literal["input_chunk"] = "input_chunk"
    text: str
    timestamp: float


class ResponseStart(BaseModel):
    id: str
    timestamp: float
    type: Literal["response_start"] = "response_start"


class ResponseDone(BaseModel):
    id: str
    timestamp: float
    type: Literal["response_done"] = "response_done"


class ResponseChunk(BaseModel):
    chunk_id: str
    response_id: str
    text: str
    timestamp: float
    type: Literal["response_chunk"] = "response_chunk"
