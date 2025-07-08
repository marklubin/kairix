from typing import Tuple

from agents import ModelProvider, Model
from llama_cpp import Llama

from kairix_core.inference.llama_cpp.model import LlamaCppModel
from kairix_core.inference.pooled_model import PooledModel

_model_definitions = {
    "nh2-mistral": {
        "repo_id": "NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF",
        "filename": "Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf"''
    }
}

class LlamaCppProvider(ModelProvider):
    def __init__(self, *args: Tuple[str, int]):
        self.model_and_pool_size: list[Tuple[str, int]] = list(args)
        for model, pool_size in self.model_and_pool_size:
            if model not in _model_definitions:
                raise ValueError(f"No model definition for {model}.")

        self.models: dict[str, PooledModel] = dict()


    #TODO - dynamic allocation or atleast bounded + load balance on hardware
    def populate(self):
        for model, pool_size in self.model_and_pool_size:
            model_pool = [
                LlamaCppModel(llama=Llama.from_pretrained(
                    repo_id=_model_definitions[model]["repo_id"],
                    filename=_model_definitions[model]["filename"],
                    n_gpu_layers=-1,  # Fixed parameter name
                    flash_attn=True,
                    n_ctx=8000,
                    use_mlock=True,
                    type_k=2,
                    type_v=2,
                    n_threads=8,
                    )
                )
                for _ in range(pool_size)
            ]
            pm = PooledModel(model_pool)
            self.models[model] = pm



    def get_model(self, model_name: str | None) -> Model:
        if not self.models:
            self.populate()

        if model_name is None or model_name not in self.models:
            raise ValueError(f"No configured model pool for {model_name}. Must configure "
                             f"when creating provider.")
        model: Model = self.models[model_name]
        return model
