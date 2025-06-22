from sentence_transformers import SentenceTransformer
from torch.distributed.elastic.utils import get_env_variable_or_raise

from kairix_core.runtime.cache import CacheRuntime
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.runtime.neo4j import Neo4jRuntime
from kairix_core.types.neo4j import Concept, SemanticLinkage
from kairix_offline.semantic_graph.types import Subject

logger = LoggingRuntime().logger
neo4j = Neo4jRuntime()

score_threshold = float(
    get_env_variable_or_raise("KAIRIX_SEMANTIC_EMBEDDING_SCORE_MERGE_THRESHOLD")
)
embedding_model = get_env_variable_or_raise("KAIRIX_SEMANTIC_EMBEDDING_MODEL")
emedding_dims = float(get_env_variable_or_raise("KAIRIX_SEMANTIC_EMBEDDING_DIMS"))

embedder = SentenceTransformer(embedding_model, truncate_dim=emedding_dims)

cache_runtime = CacheRuntime()


def upsert_concept(subject: Subject) -> Concept:
    logger.info(
        f"Creating or deduping Semantic unit for {subject.name}, type: {subject.type}."
    )
    maybe_concept = Concept.first_or_none(name=subject.name, type=subject.type)

    # Case I - Exact Match Exists - We require that both id and type of unit match
    if maybe_concept:
        logger.debug("Found exact match of type. Returning.")
        maybe_concept.occurences += 1
        maybe_concept.save()
        return maybe_concept

    # Case II - Embedding match is close enough, should match by type in search algo
    embedding = embedder.encode(subject.semantic_identifer()).tolist()
    matches: list[tuple[Concept, float]] = Concept.vector_search(embedding, 1)
    if (
        len(matches) >= 1
        and matches[0][1] >= score_threshold
        and matches[0][0].type == subject.type
    ):
        matched_concept: Concept = matches[0][0]
        logger.debug(
            f"Found semantic match via embedding index, matched is Semantic ID = [green]{matched_concept.semantic_id}[\]"
        )
        matched_concept.occurences = matched_concept.occurences + 1
        matched_concept.embedding = embedding

        # TODO considering adjusting embedding to weighted midpoint
        matched_concept.save()
        return matched_concept

    # Case III - Never node with this type and id before
    logger.debug("Did not match any extant semantic unit, creating...")
    new_concept = Concept(
        semantic_id=subject.semantic_identifer(),
        name=subject.name,
        type=subject.type,
        embedding=embedding,
    )

    new_concept.save()
    return new_concept


def upsert_linkage(s: Concept, t: Concept, linkage_type: str):
    logger.info(
        f"Handling relationship between {s.semantic_id} and {t.semantic_id}"
        f" described as {linkage_type}."
    )

    linkages: list[SemanticLinkage] = s.link.all_relationships(t)

    types_to_linkages = dict()

    for l in linkages:
        types_to_linkages[l.linkage_type] = l

    if linkage_type not in types_to_linkages:
        logger.info("Creating new relationship between Semantic Units.")
        s.link.connect(
            t,
            {
                "linkage_type": linkage_type,
            },
        )


def update_semantic_graph_from_facts():
    fact_cache = cache_runtime.facts_to_process
    facts = [fact_cache[k] for k in fact_cache]

    with neo4j.transaction():
        try:
            for fact in facts:
                s_unit = upsert_concept(fact.s)
                t_unit = upsert_concept(fact.t)
                upsert_linkage(s_unit, t_unit, fact.relationship)
            logger.info("Finished with facts commiting to db.")
        except Exception as e:
            logger.error(
                "Encounter fatal error when persisting to db, rolling back.",
                exc_info=e,
            )
            neo4j.rollback()
            raise e
