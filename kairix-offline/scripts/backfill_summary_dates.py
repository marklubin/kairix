import json
import os
from datetime import timezone, datetime

from kairix_core.types.neo4j import MemoryShard

import logging
from neomodel import db

logger = logging.getLogger()


# cat conversations.json | jq -c '.[] | {create_time: (.create_time // empty), id: (.title // empty)}'
def main():
    db_url = os.getenv("NEO4J_URL")
    db.set_connection(db_url)
    f = open("mappings.json")

    id_to_ts = dict()
    for line in f.readlines():
        d = json.loads(line)
        print(d["id"])
        id_to_ts[d["id"]] = d["create_time"]

    for shard in MemoryShard.nodes.all():
        sd = shard.source_document.single()
        if not sd:
            logger.warning("No doc for shard %s.", shard.uid)
            continue

        summary = shard.summary.single()
        if not summary:
            logger.warning("No summary for shard %s.", shard.uid)
            continue

        if sd.source_label not in id_to_ts:
            logger.warning("No Date info for source doc: %s", sd.source_label)
            continue
        ts = id_to_ts[sd.source_label]
        logger.info("Found timestamp for %s, ts: %d", sd.source_label, ts)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        logger.info("Writing out as date %s ", str(dt))
        summary.approximate_date = dt
        summary.save()


if __name__ == "__main__":
    main()
