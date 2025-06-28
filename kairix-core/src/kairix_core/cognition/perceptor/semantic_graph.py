from typing import List

from textblob import TextBlob

from kairix_core.cognition import Perceptor
from kairix_core.cognition.stores.embedded_data import EmbeddedDataStore
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.types.cognition import Perception, Stimulus
from kairix_core.types.neo4j import Concept, SemanticLinkage

logger = LoggingRuntime().logger


class SemanticGraphPerceptor(Perceptor):
    _included_pos_tags = ["FW", "NN", "RB"]

    def __init__(self, data_store: EmbeddedDataStore):
        self.data_store = data_store

    async def traverse_keyword(self, keyword: str) -> \
            list[tuple[SemanticLinkage, float]]:
        result: list[tuple[SemanticLinkage, float]] = []

        logger.info(f"Finding relationships for keyword {keyword}.")
        for semantic_id, score in self.data_store.search(keyword):
            logger.info(f"Matched to semantic id: {semantic_id}.")

            concept: Concept = Concept.nodes.first(semantic_id=semantic_id)

            for other in concept.link.all()[:10]:
                rel: SemanticLinkage = concept.link.relationship(other)
                logger.info(f"Relationship of type: {rel.linkage_type}")
                result.append((rel, score))

        return result

    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        blob: TextBlob = TextBlob(stimulus.content).correct()
        keywords = set(str(k) for k in blob.noun_phrases)

        # for word, pos in blob.tags:
        #     if pos in self._included_pos_tags:
        #         keywords.add(word)

        logger.info(f"Searching semantic graph for keywords {keywords}")
        linkages_and_scores: list[tuple[SemanticLinkage, float]] = []
        for keyword in keywords:
            results = await self.traverse_keyword(keyword)
            logger.info(f"{keyword} -  {len(results)} matches")
            linkages_and_scores.extend(results)

        logger.info("Sorting linkages and assembling perceptions.")
        sorted_linkages_and_scores: list[tuple[SemanticLinkage, float]] = sorted(
            linkages_and_scores,
            key=lambda x: x[0].score(x[1]),
            reverse=True)

        perceptions: list[Perception] = []
        for linkage, base_score in sorted_linkages_and_scores[:20]:
            logger.info(f'Including perception of semantic link "{linkage.phrase()}".')
            logger.info("Base Score: %f", base_score)
            logger.info("Adjusted Score: %d ", linkage.score(base_score))
            perceptions.append(Perception("semantic_graph.v1", linkage.phrase(), 1.0))

        return perceptions
