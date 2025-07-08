import asyncio
from typing import Any

from agents import ModelResponse, Model

from kairix_core.inference.llama_cpp.model import LlamaCppModel
from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger
class PooledModel(Model):

    def __init__(self, model_pool: list[LlamaCppModel]):
        self._pool = model_pool
        self._queue: asyncio.Queue[LlamaCppModel] | None = None

    async def initialize_with_pool(self) -> None:
        async with asyncio.Lock():
            self._queue = asyncio.Queue(len(self._pool))
            for model in self._pool:
                await self._queue.put(model)

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        if not self._queue:
            await self.initialize_with_pool()

        assert self._queue is not None, "Queue must be initialized"
        logger.info(f"Getting model from pool. Pool size: {self._queue.qsize()}")
        model = await self._queue.get()

        try:
            logger.info("Got pooled model. Generating response.")
            return await asyncio.to_thread(model.sync_complete, *args, **kwargs)
        finally:
            logger.info("Returing model.")
            assert self._queue is not None, "Queue must be initialized"
            await self._queue.put(model)
            logger.info(f"Pool size: {self._queue.qsize()}")



    def stream_response(self, *args, **kwargs):
        # checkout instance from the pool

        # stream results

        # inference ends

        # checkin instance
        raise NotImplementedError("Streaming not supported.")
