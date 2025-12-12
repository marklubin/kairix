from uuid import uuid4

from neomodel import (
    ArrayProperty,
    DateTimeProperty,
    FloatProperty,
    RelationshipTo,
    StringProperty,
    StructuredNode,
    VectorIndex,
)


class Grounding(StructuredNode):
    external_id = StringProperty(unique_index=True)
    external_label = StringProperty(required=True)
    external_source = StringProperty(required=True)


class Tag(StructuredNode):
    name = StringProperty(required=True, unique_index=True)
    created_at = DateTimeProperty(required=True)


# ------------------------------------------------------------------------------
# Block Node Definition
# ------------------------------------------------------------------------------


class Block(StructuredNode):
    # ------------------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------------------

    block_id = StringProperty(unique_index=True, default=lambda: str(uuid4()))
    content = StringProperty(required=True)
    created_at = DateTimeProperty(required=True)
    updated_at = DateTimeProperty(required=True)
    occured_at = DateTimeProperty()
    embedding_v1 = ArrayProperty(
        FloatProperty(),
        required=True,
        index=True,
        vector_index=VectorIndex(),
    )
    block_type = StringProperty(required=True)
    experience_type = StringProperty()
    interest_score = FloatProperty()
    confidence = FloatProperty()
    present_understanding = StringProperty()
    named_concept = StringProperty()
    reflection = StringProperty()
    importance = FloatProperty()
    metadata = ArrayProperty()
    
    # Agent identifier for filtering memories by agent
    agent_id = StringProperty(index=True)

    # ------------------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------------------

    tagged_with = RelationshipTo("Tag", "TAGGED_WITH")
    grounded_by = RelationshipTo("Grounding", "GROUNDED_BY")

    part_of = RelationshipTo("Block", "PART_OF")
    composed_of = RelationshipTo("Block", "PART_OF")
    derived_from = RelationshipTo("Block", "DERIVED_FROM")
    derivations_with = RelationshipTo("Block", "DERIVED_FROM")
