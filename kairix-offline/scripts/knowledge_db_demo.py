import asyncio

from agents import Agent


from sentence_transformers import SentenceTransformer

from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.runtime.neo4j import Neo4jRuntime
from kairix_core.types.neo4j import SemanticUnit, Summary
from kairix_offline.knowledge_extraction.agents import (
    world_facts_extractor,
    user_profile_extractor,
    assistant_cognitive_extractor,
)
from kairix_offline.knowledge_extraction.types import Relation, Unit

logger = LoggingRuntime().logger
neo4j = Neo4jRuntime()
agent_runtime = AgentRuntime()

embedder = SentenceTransformer(
    "sentence-transformers/all-mpnet-base-v2", device="mps", truncate_dim=128
)


async def extract_knowledge(
    summary: Summary, extraction_agents: list[Agent]
) -> list[Relation]:
    tasks_to_await = [
        agent_runtime.run(agent, summary.summary_text) for agent in extraction_agents
    ]

    results = await asyncio.gather(*tasks_to_await)
    extractions = [r.final_output for r in results]
    all_extracted_rels = []

    for a, e in zip(extraction_agents, extractions):
        logger.debug(f"Inspecting extraction for {a.name}.")

        if e and e.relationships and len(e.relationships) > 0:
            logger.debug(f"Exracted Relaitonships.{e.relationships}")
            all_extracted_rels.extend(e.relationships)
        else:
            logger.warning("Extraction was empty.")

    return all_extracted_rels


SCORE_THRESHOLD = 0.85


def upsert_semantic_unit(unit: Unit) -> SemanticUnit:
    logger.debug(
        f"Creating or deduping Semantic unit for {unit.id}, type: {unit.type}."
    )
    maybe_unit = SemanticUnit.nodes.first_or_none(uid=unit.id)

    # Case I - Exact Match Exists - We require that both id and type of unit match
    if maybe_unit and maybe_unit.type == unit.type:
        logger.debug("Found exact match of type. Returning.")
        maybe_unit.descriptions.append(unit.short_description)
        maybe_unit.occurences += 1
        maybe_unit.save()
        return maybe_unit

    # Case II - Embedding match is close enough, should match by type in search algo
    embedding = embedder.encode(unit.id)
    matches: list[tuple[SemanticUnit, float]] = SemanticUnit.vector_search(
        embedding, "embedding", 1
    )
    if (
        len(matches) >= 1
        and matches[0][1] >= SCORE_THRESHOLD
        and matches[0][0].type == unit.type
    ):
        semantic_unit: SemanticUnit = matches[0][0]
        logger.debug(
            f"Found semantic match via embedding index, matched is UID = [green]{semantic_unit.uid}[\]"
        )
        semantic_unit.occurences = semantic_unit.occurences + 1
        semantic_unit.embedding = embedding.tolist()
        semantic_unit.descriptions.append(unit.short_description)

        # TODO considering adjusting embedding to weighted midpoint
        semantic_unit.save()
        return semantic_unit

    # Case III - Never node with this type and id before

    logger.debug("Did not match any extant semantic unit, creating...")
    semantic_unit = SemanticUnit(
        uid=unit.id,
        descriptions=[unit.short_description],
        type=unit.type,
        embedding=embedding,
    )

    semantic_unit.save()
    return semantic_unit


async def extract_from_summaries(n_limit: int):
    extraction_type_id = "graph-processor-v1"
    n_limit = max(1, n_limit)
    logger.info(f"[red bold]Building knowledge graph from {n_limit} summaries.[/]")
    for i, summary in enumerate(Summary.nodes.all()):
        logger.info(f"Beginning Extraction for Summary: {summary.uid}")
        if extraction_type_id in summary.extractions_performed:
            logger.info("Already ran extraction sucessfully, skipping.")
            continue

        logger.info("Extracting Semantic Structure")
        extractions = await extract_knowledge(
            summary,
            [
                world_facts_extractor,
                user_profile_extractor,
                assistant_cognitive_extractor,
            ],
        )

        logger.info("Finished extraction...deduping and persisting to DB..")
        print(f"Processing {len(extractions)} extracted semantic units.")

        with neo4j.transaction():
            try:
                for rel in extractions:
                    u_unit = upsert_semantic_unit(rel.u)
                    v_unit = upsert_semantic_unit(rel.v)

                    logger.info(
                        f"Handling relationship between {u_unit.uid} and {v_unit.uid}"
                        f" described as {rel.relationship_descriptor}."
                    )
                    unit_relationship = u_unit.related.relationship(v_unit)
                    if unit_relationship:
                        logger.info(
                            "Adding to existing relationship and strengthing connection."
                        )
                        unit_relationship.descriptions.append(
                            rel.relationship_descriptor
                        )
                        unit_relationship.occurrences += 1
                        unit_relationship.save()
                    else:
                        logger.info("Creating new relationship between Semantic Units.")
                        u_unit.related.connect(
                            v_unit,
                            {
                                "descriptions": [rel.relationship_descriptor],
                                "occurrences": 1,
                            },
                        )
                    logger.info("Finished with extractions commiting to db.")
                    summary.extractions_performed.append(extraction_type_id)
                    summary.save()
            except Exception as e:
                logger.error(
                    "Encounter fatal error when persisting to db, rolling back.",
                    exc_info=e,
                )
                raise e

        if i >= n_limit - 1:
            break


if __name__ == "__main__":
    asyncio.run(extract_from_summaries(10))
