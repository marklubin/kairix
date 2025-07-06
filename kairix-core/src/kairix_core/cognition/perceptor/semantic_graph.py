from typing import List

from textblob import TextBlob

from kairix_core.cognition import Perceptor
from kairix_core.cognition.stores.sqlite_embedded_data import SQLiteEmbeddedDataStore
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.runtime.storage import StorageRuntime
from kairix_core.types.cognition import Perception, Stimulus
from kairix_core.types.db import Entity, SemanticLinkage

logger = LoggingRuntime().logger


class SemanticGraphPerceptor(Perceptor):
    _included_pos_tags = ["FW", "NN", "RB"]

    def __init__(self, data_store: SQLiteEmbeddedDataStore, storage: StorageRuntime = None):
        self.data_store = data_store
        self.storage = storage or StorageRuntime()

    async def traverse_keyword(self, keyword: str) -> \
            list[tuple[dict, float]]:
        result: list[tuple[dict, float]] = []

        logger.info(f"Finding relationships for keyword {keyword}.")
        for semantic_id, score in self.data_store.search(keyword):
            logger.info(f"Matched to semantic id: {semantic_id}.")

            with self.storage.session() as session:
                entity_dao = self.storage.get_dao(Entity, session)
                linkage_dao = self.storage.get_dao(SemanticLinkage, session)
                
                # Find entity by semantic_id
                entity = entity_dao.find_one_by(semantic_id=semantic_id)
                if not entity:
                    continue
                
                # Get relationships where this entity is source or target
                linkages = linkage_dao.find_all_by(source_id=entity.id) + \
                          linkage_dao.find_all_by(target_id=entity.id)
                
                for linkage in linkages[:10]:
                    # Get the related entity
                    related_id = linkage.target_id if linkage.source_id == entity.id else linkage.source_id
                    related = entity_dao.get_by_id(related_id)
                    
                    if related:
                        linkage_info = {
                            'source': entity.semantic_id,
                            'target': related.semantic_id,
                            'type': linkage.linkage_type,
                            'weight': linkage.weight
                        }
                        logger.info(f"Relationship of type: {linkage.linkage_type}")
                        result.append((linkage_info, score))

        return result

    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        blob: TextBlob = TextBlob(stimulus.content).correct()
        keywords = set(str(k) for k in blob.noun_phrases)

        # for word, pos in blob.tags:
        #     if pos in self._included_pos_tags:
        #         keywords.add(word)

        logger.info(f"Searching semantic graph for keywords {keywords}")
        linkages_and_scores: list[tuple[dict, float]] = []
        for keyword in keywords:
            results = await self.traverse_keyword(keyword)
            logger.info(f"{keyword} -  {len(results)} matches")
            linkages_and_scores.extend(results)

        logger.info("Sorting linkages and assembling perceptions.")
        sorted_linkages_and_scores: list[tuple[dict, float]] = sorted(
            linkages_and_scores,
            key=lambda x: x[1] * x[0]['weight'],  # score * weight
            reverse=True)

        perceptions: list[Perception] = []
        for linkage_info, base_score in sorted_linkages_and_scores[:20]:
            phrase = f"{linkage_info['source']} {linkage_info['type']} {linkage_info['target']}"
            logger.info(f'Including perception of semantic link "{phrase}".')
            logger.info("Base Score: %f", base_score)
            logger.info("Adjusted Score: %f", base_score * linkage_info['weight'])
            perceptions.append(Perception("semantic_graph.v1", phrase, 1.0))

        return perceptions
