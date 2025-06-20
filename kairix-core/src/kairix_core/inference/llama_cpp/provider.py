from typing import Tuple

from agents import ModelProvider, Model
from llama_cpp import Llama

from kairix_core.inference.llama_cpp.model import LlamaCppModel
from kairix_core.inference.pooled_model import PooledModel

_model_definitions = {
    "nh2-mistral": {
        "repo_id": "NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF",
        "filename": "Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf"
    }
}

class LllamaCppProvider(ModelProvider):


    #TODO - dynamic allocation or atleast bounded + load balance on hardware
    def __init__(self, *args: Tuple[str, int]):
        self.models: dict[str, PooledModel] = dict()
        for model, pool_size in args:
            if model not in _model_definitions:
                raise ValueError(f"No model definition for {model}.")

            model_pool = [
                LlamaCppModel(llama=Llama.from_pretrained(_model_definitions[model]))
                for _ in range (0, pool_size)
            ]
            self.models[model] = PooledModel(model_pool)




    def get_model(self, model_name: str | None) -> Model:
        if model_name not in self.models:
            raise ValueError(f"No configured model pool for {model_name}. Must configure "
                             f"when creating provider.")
        return self.models[model_name]
