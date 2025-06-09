import chatformat
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
        interence_parameters: InferenceParams,
    ):
        self.inference_parameters = interence_parameters
        self.model_parameters = model_parameters
        self.llm = LLM(
            model=model_parameters["model"],
            trust_remote_code=True,
            quantization="awq" if model_parameters["use_quantization"] else None,
            cpu_offload_gb=32,
        )

    def predict(self, content: str, params: InferenceParams):
        sampling_params = SamplingParams(
            max_tokens=self.inference_parameters["requested_tokens"],
            min_tokens=self.inference_parameters["requested_tokens"],
            temperature=self.inference_parameters["temperature"],
        )
        chatformat.format_chat_prompt()

        prompt = as_prompt(
            self.inference_parameters["user_prompt"],
            [
                as_message(
                    role="system", text=self.inference_parameters["system_instruction"]
                ),
                as_message(
                    role="user",
                    text=self.inference_parameters["user_prompt"],
                    content=content,
                ),
            ],
        )

        results: list[RequestOutput] = self.llm.generate(prompt, sampling_params)
        assert len(results) == 1
        output: RequestOutput = results[0]
        assert len(output.outputs) == 1
        return output.outputs[0]
