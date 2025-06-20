import asyncio
import hashlib
from typing import Iterable

from agents import Agent


from sentence_transformers import SentenceTransformer

from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.runtime.neo4j import Neo4jRuntime
from kairix_core.types.neo4j import (
    Concept,
    TrackingNode,
    Summary,
    SemanticLinkage,
)
from kairix_offline.semantic_graph.agents import (
    world_facts_extractor,
    user_profile_extractor,
    assistant_cognitive_extractor,
)
from kairix_offline.semantic_graph.types import Fact, Subject

score_threshold = 0.70
logger = LoggingRuntime().logger
neo4j = Neo4jRuntime()
agent_runtime = AgentRuntime()


embedder = SentenceTransformer(
    "sentence-transformers/all-mpnet-base-v2", device="mps", truncate_dim=128
)


async def extract_facts(text: str, extraction_agents: list[Agent]) -> list[Fact]:
    tasks_to_await = [agent_runtime.run(agent, text) for agent in extraction_agents]

    results = await asyncio.gather(*tasks_to_await)
    extractions = [r.final_output for r in results]
    all_extracted_rels = []

    for a, e in zip(extraction_agents, extractions):
        logger.debug(f"Inspecting extraction for {a.name}.")

        if e and e.facts and len(e.facts) > 0:
            logger.debug(f"Exracted Relaitonships.{e.facts}")
            all_extracted_rels.extend(e.facts)
        else:
            logger.warning("Extraction was empty.")

    return all_extracted_rels


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


def get_tracking_key(text: str):
    extraction_type_id = "graph-processor-v1"
    content_hash = hashlib.md5(text.encode()).hexdigest()
    return f"{extraction_type_id}://{content_hash}"


# Summary.nodes.all()
async def extract(texts: Iterable[str]):
    logger.info("[red bold]Starting Extraction...:")

    for i, text in enumerate(texts):
        tracking_key = get_tracking_key(text)
        if TrackingNode.get_or_none(tracking_key):
            logger.info("Already ran extraction sucessfully, skipping.")
            continue
        logger.info(
            f"Beginning Extraction for Content With Tracking Key: {tracking_key}"
        )

        logger.info("Extracting Semantic Structre")
        extractions = await extract_facts(
            text,
            [
                world_facts_extractor,
                user_profile_extractor,
                assistant_cognitive_extractor,
            ],
        )

        logger.info("Finished extraction...deduping and writing to output.")
        print(f"Processing {len(extractions)} extracted semantic units.")

        with neo4j.transaction():
            try:
                for fact in extractions:
                    s_unit = upsert_concept(fact.s)
                    t_unit = upsert_concept(fact.t)
                    upsert_linkage(s_unit, t_unit, fact.relationship)

                logger.info("Finished with extractions commiting to db.")
                TrackingNode(uid=tracking_key).save()
            except Exception as e:
                logger.error(
                    "Encounter fatal error when persisting to db, rolling back.",
                    exc_info=e,
                )
                neo4j.rollback()
                raise e


def summaries(n=3):
    yield from [s.summary_text for s in Summary.nodes.all()[0:n]]


if __name__ == "__main__":
    asyncio.run(extract(summaries()))
