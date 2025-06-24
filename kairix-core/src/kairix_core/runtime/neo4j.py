
from neomodel import config as neomodel_config
from neomodel import db

from kairix_core.cognition.stores.embedded_data import EmbeddedDataStore
from kairix_core.runtime.logging import LoggingRuntime

_NEO4J_URL = "bolt://neo4j:password@cayucos.thrush-escalator.ts.net:7687"


_KDB_EMBEDDING_QUERY = """
CALL db.index.vector.queryNodes('vector_index_Concept_embedding',
    $k, $query_vector)
YIELD node, score 
RETURN node, score 
ORDER BY score DESC
"""
logger = LoggingRuntime().logger

shard_index = {
    "index" : "vector_index_MemoryShard_vector_address",
    "content_key" : "node.shard_contents",
    "content_transform": lambda x: x[9:],
    "store_url": _NEO4J_URL

}

concept_index = {
    "index": "vector_index_Concept_embedding",
    "content_key":"node",
    "content_transform" : None,
    "store_url": _NEO4J_URL
}

class Neo4jRuntime:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self):
        neomodel_config.DATABASE_URL = _NEO4J_URL
        db.set_connection(_NEO4J_URL)

        self.embedded_memory_shard_store = EmbeddedDataStore(**shard_index)
        self.embedded_concept_store = EmbeddedDataStore(**concept_index)
