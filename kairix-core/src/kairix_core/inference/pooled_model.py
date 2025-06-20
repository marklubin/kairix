import asyncio
import queue
from concurrent.futures import ThreadPoolExecutor

from agents import ModelResponse, Model


class PooledModel(Model):

    def __init__(self, model_pool: list[Model]):
        self._pool = queue.Queue()
        for model in model_pool:
            self._pool.put(model)
        self._executor = ThreadPoolExecutor(len(self._pool))

    def _checkout(self):
        return self._pool.get(block=True)

    def _checkin(self, model):
        self._pool.put(model)

    def _blocking_get_response(self, *args, **kwargs):
        model = self._checkout()
        try:
            return model.get_response(*args, **kwargs)
        finally:
            self._checkin(model)

    async def get_response(self, *args, **kwargs) -> ModelResponse:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._blocking_get_response, *args, **kwargs)



    def stream_response(self, *args, **kwargs):
        # checkout instance from the pool

        # stream results

        # inference ends

        # checkin instance
        raise NotImplementedError("Streaming not supported.")
