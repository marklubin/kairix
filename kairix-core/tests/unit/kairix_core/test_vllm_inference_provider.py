import sys
import unittest
from types import ModuleType
from unittest.mock import Mock

# Create mock vllm module with proper class definitions
vllm_module = ModuleType("vllm")


class MockLLM:
    def __init__(
        self, model, trust_remote_code=True, quantization=None, cpu_offload_gb=32
    ):
        self.model = model
        self.trust_remote_code = trust_remote_code
        self.quantization = quantization
        self.cpu_offload_gb = cpu_offload_gb

    def generate(self, prompt, sampling_params):
        # Return mock results matching expected structure
        mock_output = Mock()
        mock_request_output = Mock()
        mock_request_output.outputs = [mock_output]
        return [mock_request_output]


class MockSamplingParams:
    def __init__(self, max_tokens=None, min_tokens=None, temperature=None):
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.temperature = temperature


class MockRequestOutput:
    pass


vllm_module.LLM = MockLLM
vllm_module.SamplingParams = MockSamplingParams
vllm_module.RequestOutput = MockRequestOutput
sys.modules["vllm"] = vllm_module

# Mock other dependencies
chatformat_module = ModuleType("chatformat")
chatformat_module.format_chat_prompt = Mock()
sys.modules["chatformat"] = chatformat_module

# Create nested transformers module structure
transformers_module = ModuleType("transformers")
transformers_models = ModuleType("transformers.models")
transformers_llama4 = ModuleType("transformers.models.llama4")
transformers_processing = ModuleType("transformers.models.llama4.processing_llama4")
transformers_processing.chat_template = Mock()

sys.modules["transformers"] = transformers_module
sys.modules["transformers.models"] = transformers_models
sys.modules["transformers.models.llama4"] = transformers_llama4
sys.modules["transformers.models.llama4.processing_llama4"] = transformers_processing

# Mock kairix_core.prompt module
prompt_module = ModuleType("kairix_core.prompt")
prompt_module.as_message = Mock(side_effect=lambda **kwargs: kwargs)
prompt_module.as_prompt = Mock(
    side_effect=lambda template, messages: "formatted_prompt"
)
sys.modules["kairix_core.prompt"] = prompt_module

from kairix_core.inference.vllm import VLLMInferenceProvider
from kairix_core.inference_provider import (
    InferenceParams,
    InferenceProvider,
    ModelParams,
)


class TestVLLMInferenceProvider(unittest.TestCase):
    def setUp(self):
        self.model_params: ModelParams = {
            "model": "test-model",
            "use_quantization": False,
        }
        self.inference_params: InferenceParams = {
            "requested_tokens": 100,
            "temperature": 0.7,
            "chat_template": "default",
            "system_instruction": "You are a helpful assistant",
            "user_prompt": "Test prompt",
        }

    def test_init_without_quantization(self):
        provider = VLLMInferenceProvider(
            model_parameters=self.model_params,
            interence_parameters=self.inference_params,
        )

        # Verify the LLM instance was created with correct parameters
        self.assertEqual(provider.llm.model, "test-model")
        self.assertEqual(provider.llm.trust_remote_code, True)
        self.assertEqual(provider.llm.quantization, None)
        self.assertEqual(provider.llm.cpu_offload_gb, 32)

        self.assertEqual(provider.model_parameters, self.model_params)
        self.assertEqual(provider.inference_parameters, self.inference_params)

    def test_init_with_quantization(self):
        model_params_with_quant = self.model_params.copy()
        model_params_with_quant["use_quantization"] = True

        provider = VLLMInferenceProvider(
            model_parameters=model_params_with_quant,
            interence_parameters=self.inference_params,
        )

        # Verify the LLM instance was created with quantization
        self.assertEqual(provider.llm.model, "test-model")
        self.assertEqual(provider.llm.trust_remote_code, True)
        self.assertEqual(provider.llm.quantization, "awq")
        self.assertEqual(provider.llm.cpu_offload_gb, 32)

    def test_predict(self):
        # Create provider
        provider = VLLMInferenceProvider(
            model_parameters=self.model_params,
            interence_parameters=self.inference_params,
        )

        # Call predict
        content = "Test content"
        params = self.inference_params.copy()
        result = provider.predict(content, params)

        # Verify chatformat.format_chat_prompt() was called
        chatformat_module.format_chat_prompt.assert_called_once()

        # Verify message creation with prompt module
        self.assertEqual(prompt_module.as_message.call_count, 2)
        prompt_module.as_message.assert_any_call(
            role="system", text="You are a helpful assistant"
        )
        prompt_module.as_message.assert_any_call(
            role="user", text="Test prompt", content="Test content"
        )

        # Verify prompt formatting
        prompt_module.as_prompt.assert_called_once()

        # Verify result is the mock output from generate
        self.assertIsNotNone(result)

    def test_inheritance(self):
        provider = VLLMInferenceProvider(
            model_parameters=self.model_params,
            interence_parameters=self.inference_params,
        )
        self.assertIsInstance(provider, InferenceProvider)

    def test_different_model_params(self):
        custom_model_params: ModelParams = {
            "model": "custom-model-path",
            "use_quantization": True,
        }

        provider = VLLMInferenceProvider(
            model_parameters=custom_model_params,
            interence_parameters=self.inference_params,
        )

        # Verify custom model parameters
        self.assertEqual(provider.llm.model, "custom-model-path")
        self.assertEqual(provider.llm.quantization, "awq")

    def test_different_inference_params(self):
        custom_inference_params: InferenceParams = {
            "requested_tokens": 200,
            "temperature": 0.9,
            "chat_template": "custom",
            "system_instruction": "Custom system instruction",
            "user_prompt": "Custom user prompt",
        }

        provider = VLLMInferenceProvider(
            model_parameters=self.model_params,
            interence_parameters=custom_inference_params,
        )

        self.assertEqual(provider.inference_parameters, custom_inference_params)


if __name__ == "__main__":
    unittest.main()
