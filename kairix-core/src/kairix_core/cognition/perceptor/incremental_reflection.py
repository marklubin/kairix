import datetime
import logging
import uuid
from typing import List

from pytz import utc  # type: ignore[import-untyped]
from sentence_transformers import SentenceTransformer

from kairix_core.cognition import Perceptor
from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.cache import CacheRuntime
from kairix_core.types.cognition import Stimulus, Perception, StimulusType
from kairix_core.types.neo4j import Agent, MemoryShard

logger = logging.getLogger(__name__)
cache = CacheRuntime().summarization_errors


class IncrementalSummarizationPerceptor(Perceptor):

    def __init__(self, *,
                 agent: Agent,
                 runtime: AgentRuntime,
                 embedder: SentenceTransformer,
                 summarization_interval: int = 20):
        self.summarization_interval = summarization_interval
        self._pending_messages: list[str] = []
        self.agent = agent
        self.runtime = runtime
        self.embedder: SentenceTransformer = embedder
        self.last_summary = ""

    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        if stimulus.type == StimulusType.user_message:
            self._pending_messages.append(f"User: {stimulus.content}")
        elif stimulus.type == StimulusType.self_perception:
            self._pending_messages.append(f"Assistant: {stimulus.content}")
        else:
            logger.info(f"{__name__} not responding to stimulus, {stimulus.type}")
            return []

        if len(self._pending_messages) >= self.summarization_interval:
            logger.info("Hit summarization interval, starting new summarization task.")

            text_to_summarize = "\n".join(self._pending_messages)
            self._pending_messages = []
            label = f"incremental-reflection-v1.{self.agent.name}.{datetime.datetime.now(tz=utc)}"

            try:
                logger.info("Invoking summarization agent.")
                summary = str(await self.runtime.run(self.agent, text_to_summarize))
                logger.info("Got back summary, generating embedding.")

                embedding = self.embedder.encode(summary).tolist()
                logger.info("Embedding completed. Persisting.")


                shard  = MemoryShard(uid=label,
                                     shard_contents= summary,
                                     vector_address= embedding)
                self.last_summary = summary
                shard.save()

            except Exception as e:
                logger.info(f"Failed to generate reflective summarization. Error was: {e}. "
                            f"Persisting to disk for later processing")
                cache[label] = text_to_summarize

        return [Perception("incremental_summary.v1", self.last_summary)] \
            if self.last_summary else []
