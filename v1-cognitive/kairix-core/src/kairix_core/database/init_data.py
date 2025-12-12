"""
Initialize database with default configuration data.

This script sets up the basic entities that the system needs to function,
including default embedding types, entity classes, linkage types, etc.
"""
from kairix_core.runtime.storage import StorageRuntime
from kairix_core.types.db import (
    EntityClass, LinkageType, EmotionalTone, EmbeddingType, Agent
)


def init_embedding_types(storage: StorageRuntime) -> None:
    """Initialize default embedding types."""
    with storage.session() as session:
        embedding_dao = storage.get_dao(EmbeddingType, session)
        
        # Check if already initialized
        if embedding_dao.count() > 0:
            return
        
        # Default embedding types from the codebase
        embeddings = [
            {
                "name": "nomic-embed-text-v1.5",
                "model_name": "nomic-embed-text-v1.5",
                "vector_length": 768
            }
        ]
        
        for emb in embeddings:
            embedding_dao.create(**emb)


def init_entity_classes(storage: StorageRuntime) -> None:
    """Initialize default entity classes."""
    with storage.session() as session:
        entity_class_dao = storage.get_dao(EntityClass, session)
        
        if entity_class_dao.count() > 0:
            return
        
        classes = [
            {
                "name": "person",
                "description": "A human being or individual",
                "positive_examples": "John Doe, Jane Smith, Dr. Watson",
                "negative_examples": "Apple Inc, New York City, dog"
            },
            {
                "name": "organization",
                "description": "A company, institution, or organized group",
                "positive_examples": "Microsoft, MIT, United Nations",
                "negative_examples": "John Doe, mountain, happiness"
            },
            {
                "name": "location",
                "description": "A place or geographical location",
                "positive_examples": "New York, Mount Everest, Pacific Ocean",
                "negative_examples": "Google, happiness, running"
            },
            {
                "name": "concept",
                "description": "An abstract idea or notion",
                "positive_examples": "democracy, love, quantum physics",
                "negative_examples": "John Doe, Apple Inc, Paris"
            },
            {
                "name": "event",
                "description": "Something that happens at a specific time",
                "positive_examples": "World War II, birthday party, conference",
                "negative_examples": "person, building, happiness"
            },
            {
                "name": "object",
                "description": "A physical thing or item",
                "positive_examples": "car, laptop, coffee mug",
                "negative_examples": "happiness, running, thinking"
            }
        ]
        
        for cls in classes:
            entity_class_dao.create(**cls)


def init_linkage_types(storage: StorageRuntime) -> None:
    """Initialize default linkage types."""
    with storage.session() as session:
        linkage_dao = storage.get_dao(LinkageType, session)
        
        if linkage_dao.count() > 0:
            return
        
        linkages = [
            {
                "name": "knows",
                "description": "Personal acquaintance or familiarity",
                "positive_examples": "friends with, colleagues, met at event",
                "negative_examples": "heard of, read about, seen on TV"
            },
            {
                "name": "related_to",
                "description": "General semantic relationship",
                "positive_examples": "similar concept, associated with, connected to",
                "negative_examples": "opposite of, unrelated, contradicts"
            },
            {
                "name": "part_of",
                "description": "Component or member relationship",
                "positive_examples": "employee of, chapter in book, wheel on car",
                "negative_examples": "owns, created by, similar to"
            },
            {
                "name": "located_in",
                "description": "Physical or conceptual location",
                "positive_examples": "lives in, office in building, idea in theory",
                "negative_examples": "owns, travels to, thinks about"
            },
            {
                "name": "synonym",
                "description": "Same or very similar meaning",
                "positive_examples": "car/automobile, big/large, happy/joyful",
                "negative_examples": "hot/cold, up/down, good/bad"
            },
            {
                "name": "antonym",
                "description": "Opposite or contrasting meaning",
                "positive_examples": "hot/cold, up/down, good/bad",
                "negative_examples": "car/automobile, big/large, happy/joyful"
            }
        ]
        
        for link in linkages:
            linkage_dao.create(**link)


def init_emotional_tones(storage: StorageRuntime) -> None:
    """Initialize default emotional tones."""
    with storage.session() as session:
        emotion_dao = storage.get_dao(EmotionalTone, session)
        
        if emotion_dao.count() > 0:
            return
        
        tones = [
            {
                "name": "happy",
                "description": "Positive, joyful emotional state",
                "positive_examples": "joyful, excited, pleased, delighted",
                "negative_examples": "sad, angry, frustrated, depressed"
            },
            {
                "name": "sad",
                "description": "Negative, sorrowful emotional state",
                "positive_examples": "depressed, melancholy, disappointed, grieving",
                "negative_examples": "happy, excited, content, joyful"
            },
            {
                "name": "angry",
                "description": "Intense negative emotion with hostility",
                "positive_examples": "furious, irritated, enraged, annoyed",
                "negative_examples": "calm, peaceful, happy, content"
            },
            {
                "name": "neutral",
                "description": "Emotionally balanced or undefined state",
                "positive_examples": "calm, objective, factual, unemotional",
                "negative_examples": "excited, angry, sad, passionate"
            },
            {
                "name": "fearful",
                "description": "Anxious or afraid emotional state",
                "positive_examples": "scared, anxious, worried, terrified",
                "negative_examples": "confident, brave, calm, relaxed"
            },
            {
                "name": "surprised",
                "description": "Unexpected or astonished reaction",
                "positive_examples": "shocked, amazed, astonished, startled",
                "negative_examples": "expected, prepared, unsurprised, bored"
            }
        ]
        
        for tone in tones:
            emotion_dao.create(**tone)


def init_default_agents(storage: StorageRuntime) -> None:
    """Initialize default agents."""
    with storage.session() as session:
        agent_dao = storage.get_dao(Agent, session)
        
        if agent_dao.count() > 0:
            return
        
        # Create default agent
        agent_dao.create(name="default")
        agent_dao.create(name="assistant")


def initialize_database(storage: StorageRuntime | None = None) -> None:
    """
    Initialize the database with all default configuration data.
    
    Args:
        storage: Optional StorageRuntime instance. Creates new if not provided.
    """
    if storage is None:
        storage = StorageRuntime()
    
    # Initialize all default data
    init_embedding_types(storage)
    init_entity_classes(storage)
    init_linkage_types(storage)
    init_emotional_tones(storage)
    init_default_agents(storage)
    
    print("Database initialized with default configuration.")


if __name__ == "__main__":
    initialize_database()