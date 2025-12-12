import argparse
import asyncio

from kairix_core.runtime.cache import CacheRuntime
from kairix_offline.commands import (
    ExtractFactsFromSummaries,
    UpdateSemanticGraphFromUnprocessedFacts,
)
from kairix_offline.jobs import (
    extract_facts_from_summaries,
    update_semantic_graph_from_facts,
)
from kairix_core.runtime.logging import LoggingRuntime


logger = LoggingRuntime().logger


async def main():
    app = argparse.ArgumentParser()
    commands = app.add_subparsers(
        dest="command", required=True, help="selected command"
    )

    # 'extract' Command
    extract = ExtractFactsFromSummaries()
    extract.register(
        commands.add_parser(
            "extract",
            aliases=["Extract", "e", "x"],
            help="extract facts from summaries",
        )
    )

    # 'update' Command
    update = UpdateSemanticGraphFromUnprocessedFacts()
    update.register(
        commands.add_parser(
            "update",
            aliases=["Update", "u", "up", "load"],
            help="Reflect all extracted facts in the runtime knowledge graph.",
        )
    )

    args = app.parse_args()

    with CacheRuntime():
        if args.command == "extract":
            return await extract_facts_from_summaries(extract.selected(args))

        if args.command == "update":
            return update_semantic_graph_from_facts()

    raise Exception("Unknown command.")


if __name__ == "__main__":
    asyncio.run(main())
