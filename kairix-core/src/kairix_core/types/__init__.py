from neomodel import (
    ArrayProperty,
    DateTimeProperty,
    FloatProperty,
    JSONProperty,
    One,
    Relationship,
    StringProperty,
    StructuredNode,
    VectorIndex,
)


class StoredLog(StructuredNode):
    uid = StringProperty(
        unique_index=True, required=True
    )  # Unique ID for the log entry
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


class MemoryShard(IdempotentNode):
    uid = StringProperty(unique_index=True, required=True)
    shard_contents = StringProperty(required=True)
    vector_address = ArrayProperty(
        FloatProperty(),
        required=True,
        index=True,
        vector_index=VectorIndex(dimensions=768),
    )

    # Relationships
    embedding = Relationship("Embedding", "HAS_EMBEDDING", cardinality=One)
    agent = Relationship("Agent", "BELONGS_TO", cardinality=One)
    source_document = Relationship("SourceDocument", "DERIVED_FROM", cardinality=One)
    summary = Relationship("Summary", "HAS_SUMMARY", cardinality=One)
    relates = Relationship("MemoryShard", "RELATES")
