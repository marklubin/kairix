import uuid
from typing import Any

from agents import  TResponseInputItem, ModelSettings, Tool, AgentOutputSchemaBase, ModelResponse, Usage
from llama_cpp import Llama, ChatCompletionRequestSystemMessage, \
    ChatCompletionRequestUserMessage, ChatCompletionRequestResponseFormat, ChatCompletionResponseChoice, ChatCompletionResponseMessage
from openai.types.responses import ResponseOutputMessage, ResponseOutputText


class LlamaCppModel:

    def __init__(self, *, llama: Llama):
        self.llama = llama

    def _get_input(self, input: str | list[TResponseInputItem]) -> str:
        if isinstance(input, str):
            return input

        assert len(input) > 0
        # TResponseInputItem is a complex type, we'll just convert to string
        return str(input[0])

    def sync_complete(self,
                      system_instructions: str | None,
                      input: str | list[TResponseInputItem],
                      model_settings: ModelSettings = ModelSettings(),
                      tools: list[Tool] = [],  # noqa
                      output_schema: AgentOutputSchemaBase | None = None,
                      *args: Any, **kwargs: Any) -> ModelResponse:  # noqa

        input_content = self._get_input(input)

        system_message = ChatCompletionRequestSystemMessage(role="system", content=system_instructions)
        user_message = ChatCompletionRequestUserMessage(role="user", content=input_content)
        messages: list[ChatCompletionRequestSystemMessage | ChatCompletionRequestUserMessage] = [system_message, user_message]

        response_format = ChatCompletionRequestResponseFormat(type="text")

        if output_schema and not output_schema.is_plain_text():
            response_format = ChatCompletionRequestResponseFormat(type="json_object",
                                                                  schema=output_schema.json_schema())

        kwargs = dict()

        if model_settings.temperature:
            kwargs['temperature'] = model_settings.temperature

        if model_settings.max_tokens:
            kwargs['max_tokens'] = model_settings.max_tokens

        if model_settings.presence_penalty:
            kwargs['presence_penalty'] = model_settings.presence_penalty

        if model_settings.frequency_penalty:
            kwargs['frequency_penalty'] = model_settings.frequency_penalty

        kwargs["response_format"] = response_format

        raw_response = self.llama.create_chat_completion(
            messages,  # type: ignore[arg-type]
            None,  # fn
            None,  # call
            None,  # tools
            **kwargs
        )
        
        # Handle streaming response type
        if hasattr(raw_response, '__iter__') and not isinstance(raw_response, dict):
            # If it's a streaming response, we need to collect it
            raise NotImplementedError("Streaming response not supported in sync_complete")
        
        raw_response = raw_response  # type: ignore[assignment]

        choices: list[ChatCompletionResponseChoice] = raw_response['choices']  # type: ignore[index]

        if not choices or not choices[0]['message']:
            raise Exception("illegal response from inference, no choices provided")

        response_message: ChatCompletionResponseMessage = choices[0]['message']

        if "content" not in response_message:
            raise Exception("Response was missisng content.")

        content = response_message.get("content", "")
        if content is None:
            content = ""
        openai_output_text = ResponseOutputText(text=content, type="output_text", annotations=[])
        openai_output_message = ResponseOutputMessage(id=f"llama::{str(uuid.uuid4())}",
                                                      role="assistant",
                                                      content=[openai_output_text],
                                                      status="completed",
                                                      type="message")

        return ModelResponse(output=[openai_output_message], usage=Usage(), response_id=None)

# def main():
#     llama = Llama.from_pretrained(
#         repo_id="NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF",
#         filename="Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf",
#         n_gpu_layers=-1,
#         flash_attn=True,
#         n_ctx=8000,
#         use_mlock=True,
#         type_k=2,
#         type_v=2
#     )
#
#     model = LlamaCppModel(llama=llama)
#     while True:
#         user_message = input("What to say to a llama?\t")
#         response: ModelResponse  =  model.get_response(system_instructions="Summarize the provided text",
#                                                             input=user_message,
#                                                             model_settings=ModelSettings(),
#                                                             tools=[],
#                                                             output_schema=None)
#         print(response.output[0].content[0].text)
#
#
# if __name__ == "__main__":
#     main()
