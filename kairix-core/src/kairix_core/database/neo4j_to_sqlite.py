"""
Convert data from Neo4j to SQLite database.

This script migrates all data from the Neo4j graph database to the new SQLite schema,
preserving relationships and vector embeddings.
"""
import logging
from typing import Dict, Optional
from datetime import datetime

from neomodel import config as neomodel_config
from neomodel import db
from sentence_transformers import SentenceTransformer
from sqlalchemy.exc import IntegrityError

from kairix_core.runtime.storage import StorageRuntime
from kairix_core.types.db import (
    Entity, EntityClass, EmbeddingType, SemanticLinkage, LinkageType, LinkageObservation,
    Agent, Source, SourceObject, MemoryShard,
    ConversationMessage
)
from kairix_core.types.neo4j import (
    Concept as Neo4jConcept,
    Agent as Neo4jAgent,
    SourceDocument as Neo4jSourceDocument,
    Summary as Neo4jSummary,
    MemoryShard as Neo4jMemoryShard
)
from kairix_core.database.init_data import initialize_database

logger = logging.getLogger(__name__)


class Neo4jToSQLiteConverter:
    """Converter for migrating data from Neo4j to SQLite."""
    
    def __init__(self, neo4j_url: str, sqlite_storage: Optional[StorageRuntime] = None):
        """
        Initialize the converter.
        
        Args:
            neo4j_url: Neo4j connection URL
            sqlite_storage: Optional SQLite storage instance
        """
        # Connect to Neo4j
        neomodel_config.DATABASE_URL = neo4j_url
        db.set_connection(neo4j_url)
        
        # Initialize SQLite
        self.storage = sqlite_storage or StorageRuntime()
        
        # Maps for tracking converted entities
        self.concept_to_entity_map: Dict[str, int] = {}
        self.agent_map: Dict[str, int] = {}
        self.source_doc_map: Dict[str, int] = {}
        self.summary_map: Dict[str, int] = {}
        
        # Initialize sentence transformer for any missing embeddings
        self.transformer = SentenceTransformer(
            "sentence-transformers/all-mpnet-base-v2",
            truncate_dim=128
        )
    
    def convert_all(self):
        """Run the complete conversion process."""
        logger.info("Starting Neo4j to SQLite conversion...")
        
        # Initialize default data
        initialize_database(self.storage)
        
        # Convert in dependency order
        self._convert_agents()
        self._convert_concepts_to_entities()
        self._convert_semantic_linkages()
        self._convert_source_documents()
        self._convert_summaries()
        self._convert_memory_shards()
        self._convert_conversation_history()
        
        logger.info("Conversion completed successfully!")
    
    def _convert_agents(self):
        """Convert Neo4j agents to SQLite."""
        logger.info("Converting agents...")
        
        with self.storage.session() as session:
            agent_dao = self.storage.get_dao(Agent, session)
            
            for neo_agent in Neo4jAgent.nodes.all():
                # Check if already exists
                existing = agent_dao.find_one_by(name=neo_agent.name)
                if existing:
                    self.agent_map[neo_agent.name] = existing.id
                else:
                    new_agent = agent_dao.create(name=neo_agent.name)
                    session.flush()
                    self.agent_map[neo_agent.name] = new_agent.id
            
            session.commit()
        
        logger.info(f"Converted {len(self.agent_map)} agents")
    
    def _convert_concepts_to_entities(self):
        """Convert Neo4j concepts to SQLite entities."""
        logger.info("Converting concepts to entities...")
        
        with self.storage.session() as session:
            entity_dao = self.storage.get_dao(Entity, session)
            entity_class_dao = self.storage.get_dao(EntityClass, session)
            embedding_dao = self.storage.get_dao(EmbeddingType, session)
            
            # Ensure we have the default embedding type
            default_embedding = embedding_dao.find_one_by(name="kairix-default-128")
            if not default_embedding:
                default_embedding = embedding_dao.create(
                    name="kairix-default-128",
                    model_name="sentence-transformers/all-mpnet-base-v2",
                    vector_length=128
                )
                session.flush()
            
            for neo_concept in Neo4jConcept.nodes.all():
                # Map concept type to entity class
                entity_class = self._map_concept_type_to_entity_class(neo_concept.type)
                
                # Ensure entity class exists
                if not entity_class_dao.find_one_by(name=entity_class):
                    entity_class_dao.create(
                        name=entity_class,
                        description=f"Migrated from concept type: {neo_concept.type}"
                    )
                    session.flush()
                
                # Convert embedding (truncate if needed)
                embedding = neo_concept.embedding
                if len(embedding) > 128:
                    embedding = embedding[:128]
                elif len(embedding) < 128:
                    # Pad with zeros
                    embedding = embedding + [0.0] * (128 - len(embedding))
                
                # Create entity
                entity = entity_dao.create(
                    semantic_id=neo_concept.semantic_id,
                    name=neo_concept.name,
                    entity_class=entity_class,
                    embedding_type="kairix-default-128",
                    embedding=embedding,
                    created_at=neo_concept.created_at or datetime.utcnow()
                )
                session.flush()
                
                self.concept_to_entity_map[neo_concept.semantic_id] = entity.id
                
                # Create observations for encounters
                if hasattr(neo_concept, 'encounters') and neo_concept.encounters:
                    from kairix_core.types.db import EntityObservation
                    obs_dao = self.storage.get_dao(EntityObservation, session)
                    
                    for encounter in neo_concept.encounters:
                        obs_dao.create(
                            entity_id=entity.id,
                            observation_type="encounter",
                            observation_value="Entity encountered",
                            approximate_occurrence=encounter if isinstance(encounter, datetime) else datetime.utcnow(),
                            source_descriptor="migrated_from_neo4j"
                        )
                
                # Add to vector index if available
                if hasattr(self.storage, 'vector_dao') and self.storage.vector_dao:
                    try:
                        self.storage.vector_dao.add_entity_embedding(entity.id, embedding)
                    except Exception as e:
                        logger.warning(f"Could not add entity to vector index: {e}")
            
            session.commit()
        
        logger.info(f"Converted {len(self.concept_to_entity_map)} concepts to entities")
    
    def _normalize_name(self, name: str) -> str:
        """Normalize names for entity classes and linkage types."""
        # Remove special characters and convert to lowercase with underscores
        import re
        normalized = re.sub(r'[^a-zA-Z0-9\s_-]', '', name)
        normalized = re.sub(r'\s+', '_', normalized)
        return normalized.lower().strip('_')
    
    def _map_concept_type_to_entity_class(self, concept_type: str) -> str:
        """Map Neo4j concept types to entity classes."""
        # Common mappings
        type_map = {
            "Person": "person",
            "Organization": "organization", 
            "Location": "location",
            "Event": "event",
            "Object": "object"
        }
        
        # Return mapped value or normalize the name
        return type_map.get(concept_type, self._normalize_name(concept_type))
    
    def _convert_semantic_linkages(self):
        """Convert Neo4j semantic linkages to SQLite."""
        logger.info("Converting semantic linkages...")
        
        # Query Neo4j for all semantic linkages
        query = """
        MATCH (source:Concept)-[r:semantic_linkage]->(target:Concept)
        RETURN source.semantic_id as source_id, 
               target.semantic_id as target_id,
               r.linkage_type as linkage_type,
               r.weight as weight,
               r.related_at as related_at,
               r.observations as observations
        """
        
        results, _ = db.cypher_query(query)
        
        with self.storage.session() as session:
            linkage_dao = self.storage.get_dao(SemanticLinkage, session)
            linkage_type_dao = self.storage.get_dao(LinkageType, session)
            obs_dao = self.storage.get_dao(LinkageObservation, session)
            
            for row in results:
                source_semantic_id = row[0]
                target_semantic_id = row[1]
                linkage_type = row[2]
                weight = row[3] or 1
                related_at = row[4]
                observations = row[5] or []
                
                # Get entity IDs
                source_id = self.concept_to_entity_map.get(source_semantic_id)
                target_id = self.concept_to_entity_map.get(target_semantic_id)
                
                if not source_id or not target_id:
                    logger.warning(f"Skipping linkage {source_semantic_id} -> {target_semantic_id}: entities not found")
                    continue
                
                # Normalize linkage type name
                normalized_linkage_type = self._normalize_name(linkage_type)
                
                # Ensure linkage type exists
                if not linkage_type_dao.find_one_by(name=normalized_linkage_type):
                    linkage_type_dao.create(
                        name=normalized_linkage_type,
                        description=f"Migrated from Neo4j: {linkage_type}"
                    )
                    session.flush()
                
                # Create semantic linkage
                try:
                    linkage_dao.create(
                        source_id=source_id,
                        target_id=target_id,
                        linkage_type=normalized_linkage_type,
                        weight=weight,
                        first_noticed_at=related_at or datetime.utcnow()
                    )
                    session.flush()
                    
                    # Create observations
                    for obs_date in observations:
                        obs_dao.create(
                            source_id=source_id,
                            target_id=target_id,
                            linkage_type=normalized_linkage_type,
                            approximate_occurrence=obs_date,
                            source_descriptor="migrated_from_neo4j"
                        )
                    
                except IntegrityError:
                    # Linkage already exists
                    logger.debug(f"Linkage already exists: {source_id} -> {target_id} ({linkage_type})")
            
            session.commit()
        
        logger.info(f"Converted {len(results)} semantic linkages")
    
    def _convert_source_documents(self):
        """Convert Neo4j source documents to SQLite sources and objects."""
        logger.info("Converting source documents...")
        
        with self.storage.session() as session:
            source_dao = self.storage.get_dao(Source, session)
            object_dao = self.storage.get_dao(SourceObject, session)
            
            # Group by source type/label
            source_groups: Dict[tuple[str, str], list] = {}
            for neo_doc in Neo4jSourceDocument.nodes.all():
                key = (neo_doc.source_type, neo_doc.source_label)
                if key not in source_groups:
                    source_groups[key] = []
                source_groups[key].append(neo_doc)
            
            # Create sources and objects
            for (source_type, source_label), docs in source_groups.items():
                # Create source
                source = source_dao.create(
                    name=f"{source_label}_{source_type}",
                    source_type=source_type,
                    format="text",  # Default format
                    processing_class="MigratedFromNeo4j",
                    configuration='{"migrated": true}'
                )
                session.flush()
                
                # Create objects
                for doc in docs:
                    obj = object_dao.create(
                        source_id=source.id,
                        object_path=doc.uid,
                        content=doc.content,
                        content_hash=doc.uid  # Use UID as hash
                    )
                    session.flush()
                    self.source_doc_map[doc.uid] = obj.id
            
            session.commit()
        
        logger.info(f"Converted {len(self.source_doc_map)} source documents")
    
    def _convert_summaries(self):
        """Convert Neo4j summaries to SQLite."""
        logger.info("Converting summaries...")
        
        with self.storage.session() as session:
            from kairix_core.types.db import Summary
            summary_dao = self.storage.get_dao(Summary, session)
            
            for neo_summary in Neo4jSummary.nodes.all():
                # Check if already exists
                existing = summary_dao.find_one_by(uid=neo_summary.uid)
                if existing:
                    self.summary_map[neo_summary.uid] = existing.id
                else:
                    # Create summary
                    summary = summary_dao.create(
                        uid=neo_summary.uid,
                        summary_text=neo_summary.summary_text,
                        extractions_performed=getattr(neo_summary, 'extractions_performed', []),
                        approximate_date=getattr(neo_summary, 'approximate_date', None),
                        created_at=neo_summary.created_at or datetime.utcnow()
                    )
                    session.flush()
                    self.summary_map[neo_summary.uid] = summary.id
            
            session.commit()
        
        logger.info(f"Converted {len(self.summary_map)} summaries")
    
    def _convert_memory_shards(self):
        """Convert Neo4j memory shards to SQLite."""
        logger.info("Converting memory shards...")
        
        with self.storage.session() as session:
            memory_dao = self.storage.get_dao(MemoryShard, session)
            embedding_dao = self.storage.get_dao(EmbeddingType, session)
            
            # Ensure embedding type exists
            default_embedding = embedding_dao.find_one_by(name="kairix-default-128")
            if not default_embedding:
                default_embedding = embedding_dao.create(
                    name="kairix-default-128",
                    model_name="sentence-transformers/all-mpnet-base-v2",
                    vector_length=128
                )
                session.flush()
            
            for neo_shard in Neo4jMemoryShard.nodes.all():
                # Get agent
                agent_name = "default"
                if neo_shard.agent.all():
                    agent_name = neo_shard.agent.all()[0].name
                agent_id = self.agent_map.get(agent_name, self.agent_map.get("default"))
                
                # Get source object
                source_object_id = None
                if neo_shard.source_document.all():
                    source_uid = neo_shard.source_document.all()[0].uid
                    source_object_id = self.source_doc_map.get(source_uid)
                
                # Convert embedding
                embedding = neo_shard.vector_address
                if len(embedding) > 128:
                    embedding = embedding[:128]
                elif len(embedding) < 128:
                    embedding = embedding + [0.0] * (128 - len(embedding))
                
                # Get summary if exists
                summary_id = None
                if hasattr(neo_shard, 'summary') and neo_shard.summary.all():
                    summary_uid = neo_shard.summary.all()[0].uid
                    summary_id = self.summary_map.get(summary_uid)
                
                # Create memory shard
                memory = memory_dao.create(
                    uid=neo_shard.uid,
                    contents=neo_shard.shard_contents,
                    embedding_type="kairix-default-128",
                    embedding=embedding,
                    agent_id=agent_id,
                    source_object_id=source_object_id,
                    summary_id=summary_id,
                    created_at=neo_shard.created_at or datetime.utcnow()
                )
                session.flush()
                
                # Add to vector index if available
                if hasattr(self.storage, 'vector_dao') and self.storage.vector_dao:
                    try:
                        self.storage.vector_dao.add_memory_embedding(memory.id, embedding)
                    except Exception as e:
                        logger.warning(f"Could not add memory to vector index: {e}")
            
            session.commit()
        
        logger.info(f"Converted {MemoryShard.nodes.count()} memory shards")
    
    def _convert_conversation_history(self):
        """Convert Neo4j conversation history to SQLite."""
        logger.info("Converting conversation history...")
        
        # Query for conversation pairs
        query = """
        MATCH (cp:ConversationPair)
        RETURN cp.agent_id as agent_id,
               cp.user_message as user_message,
               cp.assistant_message as assistant_message,
               cp.timestamp as timestamp
        ORDER BY cp.timestamp
        """
        
        results, _ = db.cypher_query(query)
        
        with self.storage.session() as session:
            msg_dao = self.storage.get_dao(ConversationMessage, session)
            agent_dao = self.storage.get_dao(Agent, session)
            
            # Group by agent
            conversations: Dict[str, list] = {}
            for row in results:
                agent_name = row[0]
                if agent_name not in conversations:
                    conversations[agent_name] = []
                conversations[agent_name].append({
                    'user': row[1],
                    'assistant': row[2],
                    'timestamp': row[3]
                })
            
            # Convert each conversation
            for agent_name, messages in conversations.items():
                # Get or create agent
                agent = agent_dao.find_one_by(name=agent_name)
                if not agent:
                    agent = agent_dao.create(name=agent_name)
                    session.flush()
                
                thread_id = f"{agent_name}_migrated"
                sequence = 1
                
                for msg_pair in messages:
                    # User message
                    msg_dao.create(
                        agent_id=agent.id,
                        user_id="migrated_user",
                        thread_id=thread_id,
                        sequence_number=sequence,
                        role="user",
                        content=msg_pair['user'],
                        created_at=msg_pair['timestamp'] or datetime.utcnow()
                    )
                    sequence += 1
                    
                    # Assistant message
                    msg_dao.create(
                        agent_id=agent.id,
                        user_id="migrated_user",
                        thread_id=thread_id,
                        sequence_number=sequence,
                        role="assistant",
                        content=msg_pair['assistant'],
                        created_at=msg_pair['timestamp'] or datetime.utcnow()
                    )
                    sequence += 1
            
            session.commit()
        
        logger.info(f"Converted {len(results)} conversation pairs")


def convert_neo4j_to_sqlite(neo4j_url: str = "bolt://neo4j:password@localhost:7687/kairix") -> None:
    """
    Convert all data from Neo4j to SQLite.
    
    Args:
        neo4j_url: Neo4j connection URL
    """
    converter = Neo4jToSQLiteConverter(neo4j_url)
    converter.convert_all()


if __name__ == "__main__":
    import sys
    
    neo4j_url = sys.argv[1] if len(sys.argv) > 1 else "bolt://neo4j:password@localhost:7687/kairix"
    
    logging.basicConfig(level=logging.INFO)
    convert_neo4j_to_sqlite(neo4j_url)