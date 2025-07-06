#!/usr/bin/env python3
"""
Validate Neo4j to SQLite migration by comparing data integrity and functionality.

This script:
1. Backs up existing Neo4j data
2. Runs the migration
3. Validates data integrity
4. Runs functional tests
5. Generates a migration report
"""
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any
import json

from neomodel import db
from kairix_core.database.neo4j_to_sqlite import Neo4jToSQLiteConverter
from kairix_core.runtime.storage import StorageRuntime
from kairix_core.types.db import (
    Agent, Entity, SemanticLinkage, MemoryShard, 
    ConversationMessage, Source, SourceObject
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MigrationValidator:
    """Validates the Neo4j to SQLite migration."""
    
    def __init__(self, neo4j_url: str, sqlite_storage: StorageRuntime = None):
        self.neo4j_url = neo4j_url
        self.storage = sqlite_storage or StorageRuntime()
        self.report: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "neo4j_url": neo4j_url,
            "validations": {},
            "errors": [],
            "warnings": []
        }
    
    def count_neo4j_nodes(self, label: str) -> int:
        """Count nodes of a specific label in Neo4j."""
        query = f"MATCH (n:{label}) RETURN count(n) as count"
        result, _ = db.cypher_query(query)
        return result[0][0] if result else 0
    
    def validate_agents(self) -> bool:
        """Validate agent migration."""
        try:
            neo4j_count = self.count_neo4j_nodes("Agent")
            
            with self.storage.session() as session:
                sqlite_count = session.query(Agent).count()
                agent_names = [a.name for a in session.query(Agent).all()]
            
            validation = {
                "neo4j_count": neo4j_count,
                "sqlite_count": sqlite_count,
                "match": neo4j_count == sqlite_count,
                "agent_names": agent_names
            }
            
            self.report["validations"]["agents"] = validation
            
            if not validation["match"]:
                self.report["errors"].append(
                    f"Agent count mismatch: Neo4j={neo4j_count}, SQLite={sqlite_count}"
                )
            
            return validation["match"]
            
        except Exception as e:
            self.report["errors"].append(f"Agent validation failed: {str(e)}")
            return False
    
    def validate_entities(self) -> bool:
        """Validate entity (concept) migration."""
        try:
            neo4j_count = self.count_neo4j_nodes("Concept")
            
            with self.storage.session() as session:
                sqlite_count = session.query(Entity).count()
                
                # Check embedding dimensions
                sample_entity = session.query(Entity).first()
                embedding_valid = True
                if sample_entity and sample_entity.embedding:
                    embedding_valid = len(sample_entity.embedding) == 128
            
            validation = {
                "neo4j_count": neo4j_count,
                "sqlite_count": sqlite_count,
                "match": neo4j_count == sqlite_count,
                "embedding_valid": embedding_valid
            }
            
            self.report["validations"]["entities"] = validation
            
            if not validation["match"]:
                self.report["errors"].append(
                    f"Entity count mismatch: Neo4j={neo4j_count}, SQLite={sqlite_count}"
                )
            
            if not embedding_valid:
                self.report["warnings"].append("Entity embeddings not properly sized (should be 128)")
            
            return validation["match"]
            
        except Exception as e:
            self.report["errors"].append(f"Entity validation failed: {str(e)}")
            return False
    
    def validate_linkages(self) -> bool:
        """Validate semantic linkage migration."""
        try:
            # Count Neo4j relationships
            query = "MATCH ()-[r:semantic_linkage]->() RETURN count(r) as count"
            result, _ = db.cypher_query(query)
            neo4j_count = result[0][0] if result else 0
            
            with self.storage.session() as session:
                sqlite_count = session.query(SemanticLinkage).count()
                
                # Check for orphaned linkages
                orphaned = session.query(SemanticLinkage).filter(
                    ~SemanticLinkage.source_id.in_(
                        session.query(Entity.id)
                    ) | ~SemanticLinkage.target_id.in_(
                        session.query(Entity.id)
                    )
                ).count()
            
            validation = {
                "neo4j_count": neo4j_count,
                "sqlite_count": sqlite_count,
                "match": neo4j_count == sqlite_count,
                "orphaned_linkages": orphaned
            }
            
            self.report["validations"]["linkages"] = validation
            
            if orphaned > 0:
                self.report["warnings"].append(f"Found {orphaned} orphaned linkages")
            
            return validation["match"]
            
        except Exception as e:
            self.report["errors"].append(f"Linkage validation failed: {str(e)}")
            return False
    
    def validate_memory_shards(self) -> bool:
        """Validate memory shard migration."""
        try:
            neo4j_count = self.count_neo4j_nodes("MemoryShard")
            
            with self.storage.session() as session:
                sqlite_count = session.query(MemoryShard).count()
                
                # Check agent associations
                unassigned = session.query(MemoryShard).filter(
                    MemoryShard.agent_id.is_(None)
                ).count()
                
                # Check embeddings
                sample = session.query(MemoryShard).first()
                embedding_valid = True
                if sample and sample.embedding:
                    embedding_valid = len(sample.embedding) == 128
            
            validation = {
                "neo4j_count": neo4j_count,
                "sqlite_count": sqlite_count,
                "match": neo4j_count == sqlite_count,
                "unassigned_shards": unassigned,
                "embedding_valid": embedding_valid
            }
            
            self.report["validations"]["memory_shards"] = validation
            
            if unassigned > 0:
                self.report["warnings"].append(f"Found {unassigned} memory shards without agents")
            
            return validation["match"]
            
        except Exception as e:
            self.report["errors"].append(f"Memory shard validation failed: {str(e)}")
            return False
    
    def validate_conversations(self) -> bool:
        """Validate conversation history migration."""
        try:
            # Count conversation pairs in Neo4j
            query = "MATCH (cp:ConversationPair) RETURN count(cp) as count"
            result, _ = db.cypher_query(query)
            neo4j_pairs = result[0][0] if result else 0
            
            with self.storage.session() as session:
                # Each pair becomes 2 messages (user + assistant)
                sqlite_count = session.query(ConversationMessage).count()
                expected_count = neo4j_pairs * 2
                
                # Check sequence integrity
                from sqlalchemy import func
                sequences = session.query(
                    ConversationMessage.thread_id,
                    func.count(ConversationMessage.id).label('count'),
                    func.max(ConversationMessage.sequence_number).label('max_seq')
                ).group_by(ConversationMessage.thread_id).all()
                
                sequence_issues = [
                    s for s in sequences 
                    if s.count != s.max_seq
                ]
            
            validation = {
                "neo4j_pairs": neo4j_pairs,
                "sqlite_messages": sqlite_count,
                "expected_messages": expected_count,
                "match": sqlite_count == expected_count,
                "sequence_issues": len(sequence_issues)
            }
            
            self.report["validations"]["conversations"] = validation
            
            if sequence_issues:
                self.report["warnings"].append(
                    f"Found {len(sequence_issues)} threads with sequence gaps"
                )
            
            return validation["match"]
            
        except Exception as e:
            self.report["errors"].append(f"Conversation validation failed: {str(e)}")
            return False
    
    def run_functional_tests(self) -> bool:
        """Run functional tests to verify behavior."""
        try:
            tests_passed = []
            
            # Test 1: Memory search
            from kairix_core.cognition.stores.sqlite_embedded_data import create_memory_shard_store
            store = create_memory_shard_store(self.storage)
            
            try:
                results = list(store.search("test query", k=5))
                tests_passed.append("memory_search")
            except Exception as e:
                self.report["errors"].append(f"Memory search test failed: {str(e)}")
            
            # Test 2: Conversation retrieval
            from kairix_core.cognition.perceptor.sqlite_conversation_history import SQLiteConversationHistoryPerceptor
            
            try:
                perceptor = SQLiteConversationHistoryPerceptor("default", self.storage)
                context = perceptor.get_recent_context(10)
                tests_passed.append("conversation_retrieval")
            except Exception as e:
                self.report["errors"].append(f"Conversation retrieval test failed: {str(e)}")
            
            # Test 3: Entity lookup
            try:
                with self.storage.session() as session:
                    entity_dao = self.storage.get_dao(Entity, session)
                    entities = entity_dao.find_all(limit=10)
                    tests_passed.append("entity_lookup")
            except Exception as e:
                self.report["errors"].append(f"Entity lookup test failed: {str(e)}")
            
            self.report["functional_tests"] = {
                "total": 3,
                "passed": len(tests_passed),
                "passed_tests": tests_passed
            }
            
            return len(tests_passed) == 3
            
        except Exception as e:
            self.report["errors"].append(f"Functional tests failed: {str(e)}")
            return False
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate final validation report."""
        # Calculate summary
        total_validations = len(self.report["validations"])
        passed_validations = sum(
            1 for v in self.report["validations"].values() 
            if v.get("match", False)
        )
        
        self.report["summary"] = {
            "total_validations": total_validations,
            "passed_validations": passed_validations,
            "error_count": len(self.report["errors"]),
            "warning_count": len(self.report["warnings"]),
            "success": passed_validations == total_validations and len(self.report["errors"]) == 0
        }
        
        return self.report
    
    def save_report(self, filename: str = "migration_validation_report.json"):
        """Save report to file."""
        with open(filename, 'w') as f:
            json.dump(self.report, f, indent=2)
        logger.info(f"Validation report saved to {filename}")


def main():
    """Run migration validation."""
    neo4j_url = sys.argv[1] if len(sys.argv) > 1 else "bolt://neo4j:password@localhost:7687/kairix"
    
    logger.info("Starting migration validation...")
    
    # Connect to Neo4j
    db.set_connection(neo4j_url)
    
    # Create validator
    validator = MigrationValidator(neo4j_url)
    
    # Run validations
    logger.info("Validating agents...")
    validator.validate_agents()
    
    logger.info("Validating entities...")
    validator.validate_entities()
    
    logger.info("Validating linkages...")
    validator.validate_linkages()
    
    logger.info("Validating memory shards...")
    validator.validate_memory_shards()
    
    logger.info("Validating conversations...")
    validator.validate_conversations()
    
    logger.info("Running functional tests...")
    validator.run_functional_tests()
    
    # Generate and save report
    report = validator.generate_report()
    validator.save_report()
    
    # Print summary
    print("\n" + "="*50)
    print("MIGRATION VALIDATION SUMMARY")
    print("="*50)
    print(f"Total Validations: {report['summary']['total_validations']}")
    print(f"Passed: {report['summary']['passed_validations']}")
    print(f"Errors: {report['summary']['error_count']}")
    print(f"Warnings: {report['summary']['warning_count']}")
    print(f"Overall Success: {report['summary']['success']}")
    print("="*50)
    
    if not report['summary']['success']:
        print("\nERRORS:")
        for error in report['errors']:
            print(f"  - {error}")
        
        print("\nWARNINGS:")
        for warning in report['warnings']:
            print(f"  - {warning}")
        
        sys.exit(1)
    else:
        print("\nMigration validation PASSED!")
        sys.exit(0)


if __name__ == "__main__":
    main()