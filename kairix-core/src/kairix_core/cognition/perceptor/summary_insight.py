import asyncio
import logging
from typing import List

import spacy.cli
import textblob
from agents import Agent

from kairix_core.prompt import agent_prompts as prompts
from kairix_core.types.cognition import Perception, Stimulus, StimulusType
from . import Perceptor
from ..stores.embedded_data import EmbeddedDataStore
from ...runtime.agent import AgentRuntime

logger = logging.getLogger(__name__)

nlp_model = "en_core_web_sm"
perception_limit_chars = 20
POS_TO_INCLUDE = [
    "PRON",
    "VERB",
    "ADJ"
]

disabled_pipes = [

]



class SummaryInsightPerceptor(Perceptor):
    def __init__(
            self,
            runtime: AgentRuntime,
            embedded_sumary_store: EmbeddedDataStore,
            k_memories: int,
    ):
        #self.query_generating_agent = Agent(name="query_generator", instructions=prompts.embedding_query_instruction_v1)
        self.insight_extraction_agent = Agent(
            name="insight_extractor",
            instructions=prompts.insight_extraction_instruction_v2,
        )

        self.embedded_summary_store = embedded_sumary_store
        self.runtime = runtime
        self.k_memories = k_memories

        # See: https://spacy.io/models TODO:DO the nlp once and use as perceptor input
        self.nlp = self._load_nlp()

    def _load_nlp(self):
        try :
            return spacy.load(nlp_model, disable=disabled_pipes)
        except Exception:
            spacy.cli.download(nlp_model)
            return spacy.load(nlp_model, disable=disabled_pipes)

    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        logger.info(f"SummaryInsightPerceptor received: {stimulus.type}")
        if stimulus.type != StimulusType.user_message:
            logger.info("...taking no action.")
            return []
        user_input: str = str(textblob.TextBlob(stimulus.content).correct())


        if len(user_input) < perception_limit_chars:
            logger.info("Input is only %i chars. Not generating insights.", len(user_input))
            return []

        keywords = self.generate_terms(user_input)


        logger.info(f"Focusing on keywords: {','.join(keywords)}")
        logger.info(f"Gathering top {self.k_memories} memories.")

        insight_sentences = set()
        for memory,_ in self.embedded_summary_store.search(' '.join(keywords), self.k_memories):
            memory_doc = self.nlp(memory)
            for ent in memory_doc.ents:
                if ent.lemma_ in keywords:
                    insight_sentences.add(ent.sent)
            for token in memory_doc:
                if token.lemma_ in keywords:
                    insight_sentences.add(token.sent)

        logger.info(f"Extracted {len(insight_sentences)} from summaries.")
        perceptions: List[Perception] = []
        for insight in insight_sentences:
            perceptions.append(
                Perception(
                    content=insight,
                    source="summary_insight_v2",
                    confidence=1.0,
                )
            )
            logger.info(f"Attaching Insight: {insight}")
        return perceptions

    async def _run_insights(self, prompts: List[str]) -> List[str]:
        tasks = [self.runtime.run(self.insight_extraction_agent, p) for p in prompts]
        results = await asyncio.gather(*tasks)
        return [r.final_output_as(str, True) for r in results]


    def generate_terms(self, user_input: str) -> set[str]:
        doc = self.nlp(user_input)
        return set(t.lemma_ for t in doc if t.pos_ in POS_TO_INCLUDE).union(
            set(ent.lemma_ for ent in doc.ents)
        )
