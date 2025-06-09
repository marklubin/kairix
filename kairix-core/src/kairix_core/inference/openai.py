from openai import OpenAI

from kairix_core.inference_provider import (
    InferenceParams,
    InferenceProvider,
    ModelParams,
)


class OpenAIInferenceProvider(InferenceProvider):
    def __init__(
        self,
        *args,
        model_parameters: ModelParams,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.model_parameters = model_parameters

        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    def predict(self, user_input: str, params: InferenceParams) -> str:
        # Build messages for OpenAI API
        messages = [
            {
                "role": "system",
                "content": params["system_instruction"],
            },
            {
                "role": "user",
                "content": params["user_prompt"].format(input=user_input),
            },
        ]

        # Make API call
        response = self.client.chat.completions.create(
            model=self.model_parameters["model"],
            messages=messages,
            temperature=params["temperature"],
            max_tokens=params["requested_tokens"],
        )

        # Extract and return the response text
        return response.choices[0].message.content
