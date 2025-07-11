from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.types.neo4j import MemoryShard
from kairix_core.runtime.neo4j import Neo4jRuntime
from kairix_core.runtime.nlp import NLPRuntime

neo4j = Neo4jRuntime()

nlp = NLPRuntime()
logger = LoggingRuntime().logger


def backfill():
    neo4j.install()
    i = 0
    input("Awaiting to proceed.")
    for shard in MemoryShard.nodes.all():
        logger.info("Processing Shard %i", i)
        logger.info("Stripping prefix %s", shard.shard_contents[:9])
        contents = shard.shard_contents[9:]
        shard.shard_contents = contents

        logger.info("Generating Embedding")
        embedding = nlp.semantic_embedder.encode(contents).tolist()
        shard.vector_address = embedding
        logger.info("Putting update.")

        shard.save()
        i += 1


if __name__ == "__main__":
    backfill()
