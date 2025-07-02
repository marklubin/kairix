from neomodel import config as neomodel_config
from neomodel import db

from kairix_core.cognition.stores.embedded_data import EmbeddedDataStore
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.types.neo4j import *  # noqa

_NEO4J_URL = "bolt://neo4j:password@localhost:7687/kairix"

_KDB_EMBEDDING_QUERY = """
CALL db.index.vector.queryNodes('vector_index_Concept_embedding',
    $k, $query_vector)
YIELD node, score 
RETURN node, score 
ORDER BY score DESC
"""
logger = LoggingRuntime().logger

shard_index = {
    "index": "vector_index_MemoryShard_vector_address",
    "content_key": "node.shard_contents",
    "store_url": _NEO4J_URL,
    "content_transform": None,
    "embedding_dims": 128

}

concept_index = {
    "index": "vector_index_Concept_embedding",
    "content_key": "node.semantic_id",
    "content_transform": None,
    "store_url": _NEO4J_URL,
    "embedding_dims": 128
}
#
# _write_pattern = r'\b(CREATE|MERGE|DELETE|DETACH\s+DELETE|SET|REMOVE)\b'
# _qcache = CacheRuntime().query_cache
#
#
# class ReadOnlyCachedNeo4j(Database):
#
#     def __init__(self):
#         super().__init__()
#         self.write_buffer = CacheRuntime().neo4j_write_buffer
#
#
#     def _is_write_query(self,cypher_query):
#         return bool(re.search(_write_pattern,
#                               cypher_query, re.IGNORECASE)
#
#     @_qcache.memoize(typed=True, name="neo4j-query")
#     def cypher_query(
#             self,
#             query: str,
#             params: Optional[dict[str, Any]] = None,
#             handle_unique: bool = True,
#             retry_on_session_expire: bool = False,
#             resolve_objects: bool = False,
#     ) -> tuple[Optional[list], Optional[tuple[str, ...]]]:
#         logger.info("Delegating to live DB.")
#         query_result = super().cypher_query(self, query, params,
#                                             handle_unique,
#                                             retry_on_session_expire,
#                                             resolve_objects)
#
#     def prewarm_cache(self):
#         for s in MemoryShard.nodes.all()



class Neo4jRuntime:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        neomodel_config.DATABASE_URL = _NEO4J_URL
        db.set_connection(_NEO4J_URL)

        self.embedded_memory_shard_store = EmbeddedDataStore(**shard_index)  # type: ignore[call-arg]
        self.embedded_concept_store = EmbeddedDataStore(**concept_index)  # type: ignore[call-arg]

    def install(self):
        db.install_all_labels()
