"""Neo4j graph database models using neomodel ORM.

This module defines all the graph nodes and relationships used in the Kairix system,
including vector-indexed nodes for semantic search capabilities.
"""

from neomodel import (
    ArrayProperty,
    DateTimeProperty,
    FloatProperty,
    JSONProperty,
    One,
    Relationship,
    StringProperty,
    StructuredNode,
    StructuredRel,
    VectorIndex,
    IntegerProperty,
)


class SemanticLinkage(StructuredRel):
    """Relationship representing semantic connections between concepts.
    
    Attributes:
        created_at: When the linkage was first created
        updated_at: When the linkage was last modified
        linkage_type: Type of semantic relationship (e.g., 'synonym', 'related')
        weight: Strength of the relationship
        encounters: Timestamps when this linkage was referenced
    """
    created_at = DateTimeProperty(default_now=True)
    updated_at = DateTimeProperty(default_now=True)
    linkage_type = StringProperty(required=True)
    weight = IntegerProperty(default=1)
    encounters = ArrayProperty(DateTimeProperty(), default=[])


    def score(self, relevance_score: float):
        return relevance_score * (
                len(self.start_node().encounters)
                + len(self.end_node().encounters)
                + int(self.weight))

    def phrase(self):
        return f"{self.start_node().name} {self.linkage_type} {self.end_node().name}"



class Concept(StructuredNode):
    """Vector-indexed node representing a semantic concept.
    
    Concepts are the building blocks of the semantic graph, representing
    entities, ideas, or relationships that can be linked semantically.
    
    Attributes:
        semantic_id: Unique identifier (format: 'type://name')
        name: Human-readable name of the concept
        type: Category/type of the concept
        created_at: When the concept was first created
        updated_at: When the concept was last modified
        encounters: Timestamps when this concept was referenced
        embedding: 128-dimensional vector representation for similarity search
    """
    VECTOR_INDEX_CONFIG = {
        "embedding": {  # property name
            "dimensions": 128,
            "similarity_function": "cosine",  # or 'euclidean'
        }
    }
    semantic_id = StringProperty(unique_index=True, required=True)
    name = StringProperty(required=True)
    type = StringProperty(required=True)
    created_at = DateTimeProperty(default_now=True)
    updated_at = DateTimeProperty(default_now=True)
    encounters = ArrayProperty(DateTimeProperty(), default=[])
    embedding = ArrayProperty(
        FloatProperty(),
        required=True,
        index=True,
        vector_index=VectorIndex(dimensions=128),
    )

    link = Relationship("Concept", "semantic_linkage", model=SemanticLinkage)

    @staticmethod
    def _composite_key(name: str, type: str):
        return f"{type}://{name}"

    @staticmethod
    def first_or_none(*, name: str, type: str):
        semantic_id = Concept._composite_key(name, type)
        return Concept.nodes.first_or_none(semantic_id=semantic_id)

    def __init__(self, **kwargs):
        name = kwargs["name"]
        type_ = kwargs["type"]

        kwargs["semantic_id"] = self._composite_key(name, type_)

        # Call parent with all kwargs
        super().__init__(**kwargs)


class StoredLog(StructuredNode):
    # Unique ID for the log entry
    uid = StringProperty(unique_index=True, required=True)
    timestamp = DateTimeProperty(required=True)  # When the log occurred
    level = StringProperty(required=True)  # Log level: e.g., 'INFO', 'ERROR'
    source = StringProperty()  # Optional: what script/module/logger
    message = StringProperty()  # Raw log message (short)
    details = JSONProperty()


class Agent(StructuredNode):
    name = StringProperty(unique_index=True, required=True)


class IdempotentNode(StructuredNode):
    __abstract_node__ = True
    uid = StringProperty(unique_index=True, required=True)

    @classmethod
    def get_or_none(cls, idempotentId):
        result = cls.nodes.filter(uid=idempotentId)
        return result[0] if result else None


class SourceDocument(IdempotentNode):
    uid = StringProperty(unique_index=True, required=True)
    source_label = StringProperty(index=True, required=True)
    source_type = StringProperty(index=True, required=True)
    content = StringProperty(required=True)


class Embedding(IdempotentNode):
    uid = StringProperty(unique_index=True, required=True)
    embedding_model = StringProperty(index=True, required=True)
    vector = ArrayProperty(
        FloatProperty(),
        required=True,
        index=True,
        vector_index=VectorIndex(dimensions=768),
    )


class Summary(IdempotentNode):
    uid = StringProperty(unique_index=True, required=True)
    summary_text = StringProperty(required=True)
    extractions_performed = ArrayProperty(StringProperty(), default=[])
    approximate_date = DateTimeProperty(required=False)


class MemoryShard(IdempotentNode):
    uid = StringProperty(unique_index=True, required=True)
    shard_contents = StringProperty(required=True)
    vector_address = ArrayProperty(
        FloatProperty(),
        required=True,
        index=True,
        vector_index=VectorIndex(dimensions=768),
    ),
    created_at = DateTimeProperty(default_now=True, required=False)

    # Relationships
    embedding = Relationship("Embedding", "HAS_EMBEDDING", cardinality=One)
    agent = Relationship("Agent", "BELONGS_TO", cardinality=One)
    source_document = Relationship(
        "SourceDocument", "DERIVED_FROM", cardinality=One)
    summary = Relationship("Summary", "HAS_SUMMARY", cardinality=One)
    relates = Relationship("MemoryShard", "RELATES")


class TrackingNode(IdempotentNode):
    uid = StringProperty(unique_index=True, required=True)
