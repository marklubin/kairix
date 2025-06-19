
from neomodel import config as neomodel_config
from neomodel import db

from kairix_core.runtime.logging import LoggingRuntime

_NEO4J_URL = "bolt://neo4j:password@cayucos.thrush-escalator.ts.net:7687"


_KDB_EMBEDDING_QUERY = """
CALL db.index.vector.queryNodes('semantic_unit_SemanticUnit_embedding',
    $k, $query_vector)
YIELD node, score 
RETURN node, score 
ORDER BY score DESC
"""
logger = LoggingRuntime().logger

class Neo4jRuntime:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self):
        neomodel_config.DATABASE_URL = _NEO4J_URL
        db.set_connection(_NEO4J_URL)
        db.install_all_labels()

    def transaction(self):
        return db.transaction
