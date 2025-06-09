import abc
from abc import ABC
from typing import TypedDict


class ModelParams(TypedDict):
    model: str
    use_quantization: bool


class InferenceParams(TypedDict):
    requested_tokens: int
    temperature: float
    chat_template: str
    system_instruction: str
    user_prompt: str


class InferenceProvider(ABC):
    @abc.abstractmethod
    def predict(self, content: str, inference_params: InferenceParams):
        raise NotImplementedError()
