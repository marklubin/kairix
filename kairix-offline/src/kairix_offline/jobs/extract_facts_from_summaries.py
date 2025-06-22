import uuid

from agents import Agent

from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.cache import CacheRuntime
from kairix_core.runtime.logging import LoggingRuntime

import asyncio

from kairix_core.types.neo4j import Summary
from kairix_offline.commands.extract import ExtractionOptions
from kairix_offline.semantic_graph.agents import (
    world_facts_extractor,
    user_profile_extractor,
    assistant_cognitive_extractor,
)
from kairix_offline.semantic_graph.types import Fact

cache_runtime = CacheRuntime()
logger = LoggingRuntime().logger
agent_runtime = AgentRuntime()


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


async def extract_facts_from_summaries(options: ExtractionOptions) -> list[Fact]:
    def generate_summaries(offset):
        yield from [s for s in Summary.nodes.all()[offset:]]

    result: list[Fact] = []
    summaries = None
    if options.is_process_all:
        summaries = Summary.nodes.all()
    else:
        summaries = generate_summaries(options.offset)

    summary_cache = cache_runtime.completed_summaries
    fact_cache = cache_runtime.extracted_facts

    new_summaries_processed = 0
    while (summary := next(summaries, None)) is not None and (
        options.is_process_all or (options.n and new_summaries_processed < options.n)
    ):
        if summary.uid in summary_cache:
            logger.info("Found summary in cache, skipping extraction.")
            continue

        logger.info("Processing summary %s.", summary.uid)

        logger.info("No cached record for summary, extracting facts.")
        facts = await do_extract(
            summary.summary_text,
            [
                world_facts_extractor,
                user_profile_extractor,
                assistant_cognitive_extractor,
            ],
        )
        logger.info("Extraction ended. Saving facts.")
        for fact in facts:
            fact_cache[str(uuid.uuid4())] = fact

        summary_cache[summary.uid] = "extracted"
        new_summaries_processed += 1
        logger.info("Saved. Extracted %i new facts from summary", len(facts))

    logger.info(
        "Processed %i new summaries, extracting %i facts.",
        new_summaries_processed,
        len(result),
    )
    return result
