"""Neo4j graph database models using neomodel ORM.

This module defines all the graph nodes and relationships used in the Kairix system,
including vector-indexed nodes for semantic search capabilities.
"""

from neomodel import (
    ArrayProperty,
    DateTimeProperty,
    FloatProperty,
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
        related_at: When the linkage was first created
        linkage_type: Type of semantic relationship (e.g., 'synonym', 'related')
        weight: Strength of the relationship
        observations: Timestamps when this linkage was referenced
    """
    related_at = DateTimeProperty(default_now=True)
    linkage_type = StringProperty(required=True)
    weight = IntegerProperty(default=1)
    observations = ArrayProperty(DateTimeProperty(), default=[])


    def score(self, relevance_score: float):
        return relevance_score * (
                len(self.start_node().observations)
                + len(self.end_node().observations)
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


class Summary(IdempotentNode):
    uid = StringProperty(unique_index=True, required=True)
    summary_text = StringProperty(required=True)
    extractions_performed = ArrayProperty(StringProperty(), default=[])
    approximate_date = DateTimeProperty(required=False)


class MemoryShard(IdempotentNode):
    VECTOR_INDEX_CONFIG = {
        "vector_address": {  # property name
            "dimensions": 128,
            "similarity_function": "cosine",  # or 'euclidean'
        }
    }
    uid = StringProperty(unique_index=True, required=True)
    shard_contents = StringProperty(required=True)
    vector_address = ArrayProperty(
        FloatProperty(),
        required=True,
        index=True,
        vector_index=VectorIndex(dimensions=128),
    )

    created_at = DateTimeProperty(default_now=True, required=False)

    agent = Relationship("Agent", "BELONGS_TO", cardinality=One)
    source_document = Relationship(
        "SourceDocument", "DERIVED_FROM", cardinality=One)
    summary = Relationship("Summary", "HAS_SUMMARY", cardinality=One)
