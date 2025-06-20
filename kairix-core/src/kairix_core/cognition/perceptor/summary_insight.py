from typing import List, Callable
from agents import Agent

from . import Perceptor
from kairix_core.types.cognition import Perception, Stimulus, StimulusType
from kairix_core.prompt import agent_prompts as prompts
import logging
import asyncio

from ...runtime.agent import AgentRuntime

logger = logging.getLogger(__name__)


class SummaryInsightPerceptor(Perceptor):
    def __init__(
        self,
        runtime: AgentRuntime,
        memory_provider: Callable[[str, int], List[str]],
        k_memories: int,
    ):
        self.query_generating_agent = Agent(name="query_generator", instructions=prompts.embedding_query_instruction_v1)
        self.insight_extraction_agent = Agent(
            name="insight_extractor",
            instructions=prompts.insight_extraction_instruction_v1,
        )

        self.memory_provider = memory_provider
        self.runtime = runtime
        self.k_memories = k_memories

    # async def perceive(self, stimulus: Stimulus) -> List[Perception]:
    #     logger.info(f"SummaryInsightPerceptor received: {stimulus.type}")
    #     if stimulus.type != StimulusType.user_message:
    #         logger.info("...taking no action.")
    #         return []
    #     user_input: str = stimulus.content
    #
    #     insights = self.memory_provider(user_input, self.k_memories)
    #     logger.info(f"Extracted {len(insights)} relevant insights.")
    #     perceptions: List[Perception] = []
    #     for insight in insights:
    #         perceptions.append(
    #             Perception(
    #                 content=insight,
    #                 source="summary_insight_v1",
    #                 confidence=1.0,  # TODO - attach vector distance
    #             )
    #         )
    #         logger.debug(f"Attaching Insight: {insight}")
    #     return perceptions

    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        logger.info(f"SummaryInsightPerceptor received: {stimulus.type}")
        if stimulus.type != StimulusType.user_message:
            logger.info("...taking no action.")
            return []
        user_input: str = stimulus.content

        # TODO - see if short circuit here if we don't need to pull mem context
        result = await self.runtime.run(self.query_generating_agent, user_input)
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
                    source="summary_insight_v1",
                    confidence=1.0,  # TODO - attach vector distance
                )
            )
            logger.debug(f"Attaching Insight: {insight}")
        return perceptions

    async def _run_insights(self, prompts: List[str]) -> List[str]:
        tasks = [self.runtime.run(self.insight_extraction_agent, p) for p in prompts]
        results = await asyncio.gather(*tasks)
        return [r.final_output_as(str, True) for r in results]
