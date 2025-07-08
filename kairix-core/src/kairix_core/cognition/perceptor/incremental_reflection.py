import datetime
import logging
from typing import List

from pytz import utc  # type: ignore[import-untyped]
from sentence_transformers import SentenceTransformer

from kairix_core.cognition import Perceptor
from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.cache import CacheRuntime
from kairix_core.runtime.storage import StorageRuntime
from kairix_core.types.cognition import Stimulus, Perception, StimulusType, K_Agent
from kairix_core.types.db import MemoryShard, Agent

logger = logging.getLogger(__name__)
cache = CacheRuntime().summarization_errors


class IncrementalReflectionPerceptor(Perceptor):

    def __init__(self, *,
                 agent: K_Agent,
                 runtime: AgentRuntime,
                 embedder: SentenceTransformer,
                 storage: StorageRuntime | None = None,
                 summarization_interval: int = 20):
        self.summarization_interval = summarization_interval
        self._pending_messages: list[str] = []
        self.agent = agent
        self.runtime = runtime
        self.embedder: SentenceTransformer = embedder
        self.storage = storage or StorageRuntime()
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

                # Get or create agent in SQLite
                with self.storage.session() as session:
                    agent_dao = self.storage.get_dao(Agent, session)
                    db_agent = agent_dao.find_one_by(name=self.agent.name)
                    if not db_agent:
                        db_agent = agent_dao.create(name=self.agent.name)
                        session.flush()
                    
                    # Create memory shard
                    memory_dao = self.storage.get_dao(MemoryShard, session)
                    memory_dao.create(
                        contents=summary,
                        embedding_type="kairix-default-128",
                        embedding=embedding[:128] if len(embedding) > 128 else embedding,
                        agent_id=db_agent.id
                    )
                    session.commit()
                    
                self.last_summary = summary

            except Exception as e:
                logger.info(f"Failed to generate reflective summarization. Error was: {e}. "
                            f"Persisting to disk for later processing")
                cache[label] = text_to_summarize

        return [Perception("incremental_summary.v1", self.last_summary)] \
            if self.last_summary else []
