"""Letta streaming provider implementation."""

from collections.abc import AsyncIterator
from logging import getLogger

from letta_client import AsyncLetta, AsyncStream
from letta_client.types.agents import AssistantMessage, LettaStreamingResponse
from rich.pretty import pretty_repr

from kairix_agent.config import Config
from kairix_agent.server.provider.base import LLMProvider

logger = getLogger()


class LettaProvider(LLMProvider):
    """Letta agent streaming provider."""

    def __init__(self, agent_id: str, base_url: str | None = None) -> None:
        if base_url is None:
            base_url = Config.LETTA_BASE_URL.value
        self.client = AsyncLetta(base_url=base_url)
        self.agent_id = agent_id

    async def stream_response(self, user_message: str) -> AsyncIterator[str]:
        response_stream: AsyncStream[
            LettaStreamingResponse
        ] = await self.client.agents.messages.stream(
            agent_id=self.agent_id, input=user_message, streaming=True, stream_tokens=True
        )

        async for response in response_stream:
            pretty_response = pretty_repr(response)
            logger.info(
                "Got letta response of type %s, with content: \n\n %s \n\n",
                response.message_type,
                pretty_response,
            )
            if isinstance(response, AssistantMessage):
                yield response.content  # type: ignore
