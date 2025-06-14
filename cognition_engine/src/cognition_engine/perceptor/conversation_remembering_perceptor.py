from typing import List, Callable
from agents import Agent, Runner

from ..types import Perception, Stimulus, StimulusType
from .base import Perceptor
import logging
import asyncio

logger = logging.getLogger(__name__)

_QUERY_INSTRUCTIONS = """
Given the current message produce a spelling corrected, normalized string of keywords and unique phrases likely
to generate meaningful semantic matches when querying embedding vector database of historical conversation summaries
that this user has taken part in before.
"""

_EXTRACT_INSTRUCTIONS = """
Given the current user message and this summary of a past interaction extract out the key details of the relevant to the current
message and provide a summarized list of no more than 5 relevant bullet points regarding, factual information, simularities
in emotional tone or parallels and deeper themes that may be relevant.
"""


class ConversationRememberingPerceptor(Perceptor):
    def __init__(
        self,
        runner: Runner,
        memory_provider: Callable[[str, int], List[str]],
        k_memories: int,
    ):
        self.query_generating_agent = Agent(
            name="query_gen",
            instructions=_QUERY_INSTRUCTIONS,
            model="gpt-4.5-preview",
        )
        self.insight_extraction_agent = Agent(
            name="insight_extractor",
            instructions=_EXTRACT_INSTRUCTIONS,
            model="gpt-4.1-nano",
        )

        self.memory_provider = memory_provider
        self.runner = runner
        self.k_memories = k_memories

    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        logger.info(f"ConversationRememberingPerceptor received: {stimulus.type}")
        if stimulus.type != StimulusType.user_message:
            logger.info("...taking no action.")
            return []
        user_input: str = stimulus.content

        result = await self.runner.run(self.query_generating_agent, user_input)
        query = result.final_output_as(str, True)

        logger.debug(f"...Embedding Store Query: {query}")

        logger.info(f"Gathering top {self.k_memories} memories...")
        memories = self.memory_provider(query, self.k_memories)
        prompts = [f"{m}\n<CURRENT_CONTEXT>{query}</CURRENT_CONTEXT>" for m in memories]

        logger.info("Running paralleized insight generation agents...")
        insights = await self._run_insights(prompts)

        logger.info(f"Extracted {len(insights)} relevant insights.")
        perceptions: List[Perception] = []
        for insight in insights:
            perceptions.append(
                Perception(
                    content=insight,
                    source="conversation_remembering_perceptor",
                    confidence=1.0,  # TODO - attach vector distance
                )
            )
            logger.debug(f"Attaching Insight: {insight}")
        return perceptions

    async def _run_insights(self, prompts: List[str]) -> List[str]:
        tasks = [self.runner.run(self.insight_extraction_agent, p) for p in prompts]
        results = await asyncio.gather(*tasks)
        return [r.final_output_as(str, True) for r in results]
