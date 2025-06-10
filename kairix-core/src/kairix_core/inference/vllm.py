import torch
from vllm import LLM, RequestOutput, SamplingParams

from kairix_core.inference_provider import (
    InferenceParams,
    InferenceProvider,
    ModelParams,
)
from kairix_core.prompt import as_message, as_prompt


class VLLMInferenceProvider(InferenceProvider):
    def __init__(
        self,
        *args,
        model_parameters: ModelParams,
    ):
        self.model_parameters = model_parameters
        model_id = "unsloth/tinyllama-bnb-4bit"
        self.llm = LLM(
            model=model_id,
            dtype=torch.bfloat16,
            trust_remote_code=True,
            quantization="bitsandbytes",
            load_format="bitsandbytes",
        )
        # self.llm = LLM(
        #     model=model_parameters["model"],
        #     # trust_remote_code=True,
        #     # kv_cache_dtype="fp8",
        #     max_model_len=4096,
        #     # calculate_kv_scales=True,
        #     quantization="awq" if model_parameters["use_quantization"] else None,
        # )

    def predict(self, user_input: str, params: InferenceParams) -> str:
        sampling_params = SamplingParams(
            max_tokens=params["requested_tokens"],
            min_tokens=params["requested_tokens"],
            temperature=params["temperature"],
        )
        # Assert that required parameters are provided and are strings
        assert params["system_instruction"] is not None, (
            "system_instruction is required"
        )
        assert params["user_prompt"] is not None, "user_prompt is required"
        assert isinstance(params["system_instruction"], str), (
            "system_instruction must be a string"
        )
        assert isinstance(params["user_prompt"], str), "user_prompt must be a string"

        prompt = as_prompt(
            params["chat_template"],
            [
                as_message(
                    role="system",
                    content=params["system_instruction"],
                ),
                as_message(
                    role="user",
                    content=params["user_prompt"],
                    input=user_input,
                ),
            ],
        )

        results: list[RequestOutput] = self.llm.generate(prompt, sampling_params)
        assert len(results) == 1
        output: RequestOutput = results[0]
        assert len(output.outputs) == 1
        assert hasattr(output.outputs[0], "text")
        return str(output.outputs[0].text)
