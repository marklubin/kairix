import json
import logging
from typing import Any

import rich.logging as richlogging
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
)

from kairix_core.inference_provider import (
    InferenceParams,
    InferenceProvider,
    ModelParams,
)


def dump_obj(obj: Any) -> str:
    return json.dumps(obj, indent=4, default=str)


wirelog = logging.getLogger("wirelog:" + __name__)
wirelog.propagate = False

wirelog.addHandler(richlogging.RichHandler())
wirelog.addHandler(logging.FileHandler("wirelog.log"))


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
        messages: list[ChatCompletionMessageParam] = []

        # System instruction is optional but must be string if provided
        if params["system_instruction"] is not None:
            assert isinstance(params["system_instruction"], str), (
                "system_instruction must be a string"
            )
            system_msg: ChatCompletionSystemMessageParam = {
                "role": "system",
                "content": params["system_instruction"],
            }

            messages.append(system_msg)
        # User prompt is optional but must be string if provided
        if params["user_prompt"] is not None:
            assert isinstance(params["user_prompt"], str), (
                "user_prompt must be a string"
            )
            user_messsage_content = params["user_prompt"].format(input=user_input)
        else:
            user_messsage_content = user_input

        messages.append(
            {
                "role": "user",
                "content": user_messsage_content,
            }
        )

        wirelog.info(f"<REQUEST>\n {dump_obj(messages)}\n</REQUEST>")

        # Make API call
        response = self.client.chat.completions.create(
            model=self.model_parameters["model"],
            messages=messages,
            temperature=params["temperature"],
            max_tokens=params["requested_tokens"],
        )

        wirelog.info(f"RESPONSE>\n {dump_obj(response)}\n</RESPONSE>")

        assert response.choices is not None and len(response.choices) > 0
        choice = response.choices[0]
        message = choice.message
        return str(message.content)
