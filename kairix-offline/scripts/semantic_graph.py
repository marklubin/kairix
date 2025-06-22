import argparse
import asyncio
import uuid
from typing import Iterable

import diskcache
from agents import Agent

from sentence_transformers import SentenceTransformer

from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.runtime.neo4j import Neo4jRuntime
from kairix_core.types.neo4j import (
    Concept,
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
    "sentence-transformers/all-mpnet-base-v2", truncate_dim=128
)


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


def update_semantic_graph_with_facts(facts: Iterable[Fact]):
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


async def do_extract(text: str, extraction_agents: list[Agent]) -> list[Fact]:
    tasks_to_await = [agent_runtime.run(agent, text) for agent in extraction_agents]

    logger.info("Starting concurrent extraction.")
    results = await asyncio.gather(*tasks_to_await)
    extractions = [r.final_output for r in results]
    all_facts = []
    logger.info("Received extracted results. Preparing facts.")

    for a, e in zip(extraction_agents, extractions):
        logger.info(f"Inspecting extraction for agent {a.name}.")

        if e and e.facts and len(e.facts) > 0:
            logger.info(f"Exracted Facts: {str(e.facts)}")
            all_facts.extend(e.facts)
        else:
            logger.warning("Extraction was empty.")

    return all_facts


async def extract_facts_from_summaries(
    summaries: Iterable[Summary], cache: diskcache.Cache
) -> list[Fact]:
    result: list[Fact] = []
    new_summaries_processed: int = 0
    for i, summary in enumerate(summaries):
        if summary.uid in cache:
            logger.info("Found summary in cache, skipping extraction.")
            continue

        logger.info("Processing summary %d, Title: %s.", i, summary.uid)

        logger.info("No cached record for summary, extracting facts.")
        extractions = await do_extract(
            summary.summary_text,
            [
                world_facts_extractor,
                user_profile_extractor,
                assistant_cognitive_extractor,
            ],
        )
        logger.info("Extraction ended.")
        result.extend(extractions)
        cache[summary.uid] = "extracted"
        new_summaries_processed += 1
        logger.info("Extracted %i new facts from summary", len(extractions))

    logger.info(
        "Processed %i new summaries, extracting %i facts.",
        new_summaries_processed,
        len(result),
    )
    return result


def summaries(offset=0, n=3):
    yield from [s for s in Summary.nodes.all()[offset:n]]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", type=str)

    args = parser.parse_args()
    extraction_cache = diskcache.Cache(".cache/summary-extraction")
    fact_cache = diskcache.Cache(".cache/facts")

    try:
        if args.command == "summary-extraction":
            facts_to_process = await extract_facts_from_summaries(
                summaries(), extraction_cache
            )
            for fact in facts_to_process:
                fact_cache[str(uuid.uuid4())] = fact

        if args.command == "write-facts":
            update_semantic_graph_with_facts([fact_cache[k] for k in fact_cache])
            fact_cache.clear()

    finally:
        extraction_cache.close()
        fact_cache.close()


if __name__ == "__main__":
    asyncio.run(main())
