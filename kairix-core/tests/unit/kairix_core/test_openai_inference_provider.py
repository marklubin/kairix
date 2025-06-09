import unittest
from unittest.mock import Mock, patch

from kairix_core.inference.openai import OpenAIInferenceProvider
from kairix_core.inference_provider import InferenceParams, ModelParams


class TestOpenAIInferenceProvider(unittest.TestCase):
    def setUp(self):
        self.model_params: ModelParams = {
            "model": "gpt-4",
            "use_quantization": False,
        }
        self.inference_params: InferenceParams = {
            "requested_tokens": 100,
            "temperature": 0.7,
            "chat_template": "default",
            "system_instruction": "You are a helpful assistant",
            "user_prompt": "Answer this: {input}",
        }

    @patch("kairix_core.inference.openai.OpenAI")
    def test_init_with_base_url(self, mock_openai_class):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        provider = OpenAIInferenceProvider(
            model_parameters=self.model_params,
            api_key="test-key",
            base_url="https://custom.openai.com",
        )

        # Verify OpenAI client was initialized with correct parameters
        mock_openai_class.assert_called_once_with(
            api_key="test-key",
            base_url="https://custom.openai.com",
        )
        self.assertEqual(provider.client, mock_client)
        self.assertEqual(provider.model_parameters, self.model_params)

    @patch("kairix_core.inference.openai.OpenAI")
    def test_predict_happy_path(self, mock_openai_class):
        # Setup mock response
        mock_message = Mock()
        mock_message.content = "This is the AI response"
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response = Mock()
        mock_response.choices = [mock_choice]

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        provider = OpenAIInferenceProvider(
            model_parameters=self.model_params,
        )

        # Call predict
        result = provider.predict("What is 2+2?", self.inference_params)

        # Verify the API was called correctly
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Answer this: What is 2+2?"},
            ],
            temperature=0.7,
            max_tokens=100,
        )

        # Verify result
        self.assertEqual(result, "This is the AI response")

    @patch("kairix_core.inference.openai.OpenAI")
    def test_predict_bad_input(self, mock_openai_class):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        provider = OpenAIInferenceProvider(
            model_parameters=self.model_params,
        )

        # Test with None input
        with self.assertRaises(TypeError):
            provider.predict(None, self.inference_params)

        # Test with empty params
        with self.assertRaises(KeyError):
            provider.predict("test", {})

    @patch("kairix_core.inference.openai.OpenAI")
    def test_predict_service_failure(self, mock_openai_class):
        mock_client = Mock()
        # Simulate API error
        mock_client.chat.completions.create.side_effect = Exception("OpenAI API Error")
        mock_openai_class.return_value = mock_client

        provider = OpenAIInferenceProvider(
            model_parameters=self.model_params,
        )

        # Should raise the exception from the API
        with self.assertRaises(Exception) as context:
            provider.predict("Test input", self.inference_params)

        self.assertEqual(str(context.exception), "OpenAI API Error")


if __name__ == "__main__":
    unittest.main()
