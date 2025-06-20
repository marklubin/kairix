import asyncio
import uuid
from typing import AsyncIterator

from agents import Model, TResponseInputItem, ModelSettings, Tool, AgentOutputSchemaBase, Handoff, ModelTracing, \
    ModelResponse, Usage
from agents.items import TResponseStreamEvent
from llama_cpp import Llama, ChatCompletionRequestSystemMessage, \
    ChatCompletionRequestUserMessage, ChatCompletionRequestResponseFormat, CreateChatCompletionResponse, \
    ChatCompletionResponseChoice, ChatCompletionResponseMessage
from openai.types.responses import ResponsePromptParam, ResponseOutputMessage, ResponseOutputText

from kairix_core.runtime.logging import LoggingRuntime


class LlamaCppModel(Model):


    def __init__(self, *, llama: Llama):
       self.llama = llama


    async def get_response(self,
                           system_instructions: str | None,
                           input: str | list[TResponseInputItem],
                           model_settings: ModelSettings=ModelSettings(),
                           tools: list[Tool]=[], # noqa
                           output_schema: AgentOutputSchemaBase | None=None,
                           handoffs: list[Handoff]=[], *args, **kwargs) -> ModelResponse: #noqa

        if type(input) is not str:
            raise Exception("only string inputs are presently supported.")

        system_message = ChatCompletionRequestSystemMessage(role="system", content=system_instructions)
        user_message = ChatCompletionRequestUserMessage(role="user", content=input)
        messages = [system_message, user_message]

        response_format = ChatCompletionRequestResponseFormat(type="text")

        if output_schema and not output_schema.is_plain_text():
            response_format = ChatCompletionRequestResponseFormat(type="json_object",
                                                                  schema=output_schema.json_schema())

        kwargs = dict()

        if model_settings.temperature:
            kwargs['tempature'] = model_settings.temperature

        if model_settings.max_tokens:
            kwargs['max_tokens'] = model_settings.max_tokens

        if model_settings.presence_penalty:
            kwargs['presence_penalty'] = model_settings.presence_penalty

        if model_settings.frequency_penalty:
            kwargs['frequency_penalty'] = model_settings.frequency_penalty

        kwargs["response_format"] = response_format

        raw_response: CreateChatCompletionResponse = (
            self.llama.create_chat_completion(messages,
                                            None,  # fn
                                            None,  # call
                                            None,  # tools
                                            **kwargs))

        choices: list[ChatCompletionResponseChoice] = raw_response['choices']

        if not choices or len(choices) == 0 or not choices[0] or not choices[0]['message']:
            raise Exception("illegal response from inference, no choices provided")

        response_message: ChatCompletionResponseMessage = choices[0]['message']

        if "content" not in response_message:
            raise Exception("Response was missisng content.")


        openai_output_text = ResponseOutputText(text=response_message["content"], type="output_text", annotations=[])
        openai_output_message = ResponseOutputMessage(id=f"llama::{str(uuid.uuid4())}",
                                                      role="assistant",
                                                      content=[openai_output_text],
                                                      status="completed",
                                                      type="message")

        return ModelResponse(output=[openai_output_message], usage=Usage(), response_id=None)

    def stream_response(self,
                        system_instructions: str | None,
                        input: str | list[TResponseInputItem],
                        model_settings: ModelSettings,
                        tools: list[Tool],
                        output_schema: AgentOutputSchemaBase | None,
                        handoffs: list[Handoff],
                        tracing: ModelTracing,
                        *,
                        previous_response_id: str | None,
                        prompt: ResponsePromptParam | None) -> AsyncIterator[TResponseStreamEvent]:
        raise NotImplementedError("Streaming not yet supported with llama.cpp.")


async def main():
    logger = LoggingRuntime().logger
    llama = Llama.from_pretrained(
        repo_id="NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF",
        filename="Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf",
        n_gpu_layers=-1,
        flash_attn=True,
        n_ctx=8000,
        use_mlock=True,
        type_k=2,
        type_v=2
    )

    model = LlamaCppModel(llama=llama)
    while True:
        user_message = input("What to say to a llama?\t")
        response: ModelResponse  = await model.get_response(system_instructions="Summarize the provided text",
                                                            input=user_message,
                                                            model_settings=ModelSettings(),
                                                            tools=[],
                                                            output_schema=None)
        print(response.output[0].content[0].text)


if __name__ == "__main__":

   asyncio.run(main())
