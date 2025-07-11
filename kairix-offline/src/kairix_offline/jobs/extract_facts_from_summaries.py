import asyncio
import itertools
import os
import uuid
from typing import Iterable, Tuple

from agents import Agent

from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.cache import CacheRuntime
from kairix_core.runtime.logging import LoggingRuntime

from kairix_core.types.neo4j import Summary
from kairix_offline.commands.extract import ExtractionOptions
from kairix_offline.semantic_graph.agents import (
    world_facts_extractor,
    user_profile_extractor,
    assistant_cognitive_extractor,
)
from kairix_offline.semantic_graph.types import Fact, Extract

cache_runtime = CacheRuntime()
logger = LoggingRuntime().logger
agent_runtime = AgentRuntime()

facts_cache = cache_runtime.extracted_facts
extraction_processing_records = cache_runtime.extraction_processing_records
exceptions = cache_runtime.extraction_exceptions

from rich.pretty import pretty_repr

extraction_agents = [
    world_facts_extractor,
    user_profile_extractor,
    assistant_cognitive_extractor,
]

max_concurrent_extractions = (
    int(os.getenv("KAIRIX_SUMMARY_EXTRACTION_PARALLELISM")) or 5
)

semaphore = asyncio.Semaphore(max_concurrent_extractions)


async def _run_internal(summary: Summary, agent: Agent) -> list[Fact]:
    extraction_key = f"{agent.name}-{summary.uid}"

    if extraction_key in extraction_processing_records:
        logger.info("Extraction already processed for %s, continuing.", extraction_key)
        return []

    text: str = str(summary.summary_text)
    logger.info(
        "Agent: %s, Summary: %s - waiting for semaphore.", agent.name, summary.uid
    )
    async with semaphore:
        logger.info(
            "Agent: %s, Summary: %s -  starting extraction.", agent.name, summary.uid
        )
        results = await agent_runtime.run(agent, text)

    extract: Extract = results.final_output
    logger.info("Agent: %s, finished extraction.", agent.name)
    logger.info("Received extracted results. Preparing facts.")

    if not extract.facts:
        logger.warn("Received Extract with no facts.")
    for fact in extract.facts:
        approximate_date = (
            summary.approximate_date if summary.approximate_date else None
        )
        facts_cache[str(uuid.uuid4())] = (fact, approximate_date)

    extraction_processing_records[extraction_key] = True
    logger.info("Saved. Extracted %i new facts from summary", len(extract.facts))

    return extract.facts


async def run_extraction(summary: Summary, agent: Agent):
    try:
        return await _run_internal(summary, agent)
    except Exception as e:
        exc_type = type(e)
        if exc_type not in exceptions:
            exceptions[exc_type] = []
        logger.error(
            "Encountered Exception while running extraction persisting: %s.", e
        )

        exception_log = (
            f"Failured on Summary: {summary.uid}"
            f" Agent: {agent.name} was: {pretty_repr(e)}"
        )
        exceptions[exc_type].append(exception_log)
    return None


async def extract_facts_from_summaries(options: ExtractionOptions):
    summaries = Summary.nodes.all()

    if not options.is_process_all and options.offset:
        summaries = summaries[options.offset :]

    if not options.is_process_all and options.n:
        summaries = summaries[: options.n]

    agent_cycle = itertools.cycle(extraction_agents)
    extractions: Iterable[Tuple[Agent, Summary]] = zip(agent_cycle, summaries)

    tasks = [asyncio.create_task(run_extraction(s, a)) for a, s in extractions]

    await asyncio.gather(*tasks)

    logger.info("Processed all requested summaries..")
