#!/usr/bin/env python3
"""Initialize a new user database with default categories and values."""
import sys
import sqlite3
from pathlib import Path

def create_database(db_path: str) -> None:
    """Create a new database with default schema and values."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create all tables
    cursor.executescript("""
    -- Core tables
    CREATE TABLE agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE entity_class (
        name TEXT PRIMARY KEY,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE linkage_type (
        name TEXT PRIMARY KEY,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        semantic_id TEXT NOT NULL,
        entity_class TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (entity_class) REFERENCES entity_class(name)
    );
    
    CREATE TABLE semantic_linkages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        linkage_type TEXT NOT NULL,
        weight REAL DEFAULT 1.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (linkage_type) REFERENCES linkage_type(name)
    );
    
    CREATE TABLE memory_shards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid TEXT UNIQUE,
        contents TEXT NOT NULL,
        embedding_type TEXT,
        embedding BLOB,
        agent_id INTEGER NOT NULL,
        summary_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (agent_id) REFERENCES agents(id)
    );
    
    CREATE TABLE conversation_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        thread_id TEXT NOT NULL,
        sequence_number INTEGER NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
        content TEXT NOT NULL,
        metadata JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (agent_id) REFERENCES agents(id),
        UNIQUE(thread_id, sequence_number)
    );
    
    CREATE TABLE entity_observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        observation_type TEXT,
        observation_data JSON,
        FOREIGN KEY (entity_id) REFERENCES entities(id)
    );
    
    CREATE TABLE linkage_observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        linkage_id INTEGER NOT NULL,
        observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        observation_type TEXT,
        observation_data JSON,
        FOREIGN KEY (linkage_id) REFERENCES semantic_linkages(id)
    );
    
    -- Default entity classes
    INSERT INTO entity_class (name, description) VALUES
        ('person', 'Human entity - individuals mentioned or interacted with'),
        ('location', 'Physical or virtual locations'),
        ('organization', 'Companies, groups, institutions'),
        ('event', 'Temporal occurrences or happenings'),
        ('concept', 'Abstract ideas or themes'),
        ('object', 'Physical items or artifacts'),
        ('date', 'Specific dates or time periods'),
        ('url', 'Web addresses and links'),
        ('emotion', 'Feelings or emotional states'),
        ('skill', 'Abilities or competencies');
    
    -- Default linkage types
    INSERT INTO linkage_type (name, description) VALUES
        ('related_to', 'General relationship between entities'),
        ('located_at', 'Entity is at a location'),
        ('works_for', 'Employment relationship'),
        ('knows', 'Personal acquaintance'),
        ('participates_in', 'Participation in event'),
        ('owns', 'Ownership relationship'),
        ('created_by', 'Creation relationship'),
        ('mentioned_with', 'Co-occurrence in context'),
        ('causes', 'Causal relationship'),
        ('precedes', 'Temporal ordering');
    
    -- Default agent
    INSERT INTO agents (name) VALUES ('default');
    """)
    
    conn.commit()
    conn.close()
    print(f"Created database: {db_path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: init_user_db.py <username>")
        sys.exit(1)
    
    username = sys.argv[1]
    db_dir = Path.home() / "kairix" / ".sqlite"
    db_dir.mkdir(parents=True, exist_ok=True)
    
    db_path = db_dir / f"{username}.db"
    
    if db_path.exists():
        print(f"Database already exists: {db_path}")
        response = input("Overwrite? (y/N): ")
        if response.lower() != 'y':
            sys.exit(0)
        db_path.unlink()
    
    create_database(str(db_path))
    
    # Create symlink in current directory if requested
    if len(sys.argv) > 2 and sys.argv[2] == "--link":
        local_link = Path("kairix.db")
        if local_link.exists():
            local_link.unlink()
        local_link.symlink_to(db_path)
        print(f"Created symlink: kairix.db -> {db_path}")

if __name__ == "__main__":
    main()