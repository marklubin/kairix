#!/usr/bin/env python3
"""
Run the Neo4j to SQLite migration with validation.

Usage:
    python run_migration.py [neo4j_url] [--validate] [--backup]
"""
import sys
import logging
import argparse
from datetime import datetime
import shutil
import os

from kairix_core.database.neo4j_to_sqlite import convert_neo4j_to_sqlite
from kairix_core.database.init_data import initialize_database
from kairix_core.runtime.storage import StorageRuntime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backup_sqlite_db(db_path: str = "kairix.db") -> str:
    """Create a backup of the SQLite database."""
    if os.path.exists(db_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.backup_{timestamp}"
        shutil.copy2(db_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    return ""


def main():
    parser = argparse.ArgumentParser(description="Run Neo4j to SQLite migration")
    parser.add_argument(
        "neo4j_url",
        nargs="?",
        default="bolt://neo4j:password@localhost:7687/kairix",
        help="Neo4j connection URL"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validation after migration"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Backup existing SQLite database before migration"
    )
    parser.add_argument(
        "--sqlite-path",
        default="kairix.db",
        help="Path to SQLite database file"
    )
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("NEO4J TO SQLITE MIGRATION")
    logger.info("="*60)
    logger.info(f"Neo4j URL: {args.neo4j_url}")
    logger.info(f"SQLite Path: {args.sqlite_path}")
    
    # Backup if requested
    if args.backup:
        backup_path = backup_sqlite_db(args.sqlite_path)
    
    try:
        # Initialize SQLite storage
        storage = StorageRuntime(db_url=f"sqlite:///{args.sqlite_path}")
        
        # Initialize database schema and default data
        logger.info("\nInitializing SQLite database...")
        initialize_database(storage)
        
        # Run migration
        logger.info("\nStarting migration...")
        start_time = datetime.now()
        
        convert_neo4j_to_sqlite(args.neo4j_url)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"\nMigration completed in {duration.total_seconds():.2f} seconds")
        
        # Run validation if requested
        if args.validate:
            logger.info("\nRunning validation...")
            from scripts.validate_migration import MigrationValidator
            
            validator = MigrationValidator(args.neo4j_url, storage)
            validator.validate_agents()
            validator.validate_entities()
            validator.validate_linkages()
            validator.validate_memory_shards()
            validator.validate_conversations()
            validator.run_functional_tests()
            
            report = validator.generate_report()
            validator.save_report()
            
            if report['summary']['success']:
                logger.info("✅ Validation PASSED!")
            else:
                logger.error("❌ Validation FAILED!")
                logger.error(f"Errors: {report['summary']['error_count']}")
                logger.error(f"Warnings: {report['summary']['warning_count']}")
                sys.exit(1)
        
        logger.info("\n✅ Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"\n❌ Migration failed: {str(e)}")
        logger.exception(e)
        
        # Restore backup if it exists
        if args.backup and backup_path and os.path.exists(backup_path):
            logger.info(f"Restoring from backup: {backup_path}")
            shutil.copy2(backup_path, args.sqlite_path)
        
        sys.exit(1)


if __name__ == "__main__":
    main()