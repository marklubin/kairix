from unittest.mock import MagicMock
import os
import sys

# Prevent any imports that might connect to database
os.environ['TESTING'] = '1'
os.environ.pop('NEO4J_URL', None)
os.environ.pop('KAIRIX_DATABASE_URL', None)
os.environ.pop('DATABASE_URL', None)

import numpy as np
import pytest

SUMMARY_TEXT = "summary-summary"
NP_EMBEDDING = np.random.rand(768)
VECTOR_EMBEDDING = NP_EMBEDDING.tolist()

# Global container instance
_neo4j_container = None


def pytest_sessionstart(session):
    """Start Neo4j container before any tests or imports."""
    global _neo4j_container
    
    import os
    
    # Clear any existing database URLs
    for var in ['NEO4J_URL', 'KAIRIX_DATABASE_URL', 'DATABASE_URL']:
        if var in os.environ:
            del os.environ[var]

    from testcontainers.neo4j import Neo4jContainer

    _neo4j_container = (
        Neo4jContainer("neo4j:5")
        .with_env("NEO4J_AUTH", "neo4j/password")  # Fixed credentials
        .with_env("NEO4J_PLUGINS", '["apoc", "genai"]')
        .with_env("NEO4J_apoc_export_file_enabled", "true")
        .with_env("NEO4J_apoc_import_file_enabled", "true")
        .with_env("NEO4J_apoc_import_file_use__neo4j__config", "true")
        .with_env("NEO4J_server_memory_pagecache_size", "512M")
        .with_env("NEO4J_server_memory_heap_initial__size", "512M")
        .with_env("NEO4J_server_memory_heap_max__size", "2G")
        .with_env("NEO4J_dbms_security_procedures_unrestricted", "apoc.*,genai.*")
        .with_env("NEO4J_dbms_security_procedures_allowlist", "apoc.*,genai.*")
    )
    _neo4j_container.start()

    # Get connection URL and add credentials manually
    base_url = _neo4j_container.get_connection_url()
    # Extract host:port from the URL
    import re
    match = re.search(r'bolt://(?:[^@]+@)?(.+)', base_url)
    if match:
        host_port = match.group(1)
    else:
        host_port = base_url.replace('bolt://', '')
    
    # Build URL with our credentials
    test_db_url = f"bolt://neo4j:password@{host_port}"
    
    # Set environment variables BEFORE importing neomodel
    os.environ['NEO4J_URL'] = test_db_url
    os.environ['KAIRIX_DATABASE_URL'] = test_db_url
    os.environ['DATABASE_URL'] = test_db_url
    
    # NOW import and configure neomodel
    from neomodel import config as neomodel_config
    from neomodel import db
    
    neomodel_config.DATABASE_URL = test_db_url
    
    # Wait for database to be ready
    import time
    max_retries = 30
    for i in range(max_retries):
        try:
            db.cypher_query("RETURN 1")
            print(f"Neo4j container ready at {test_db_url}")
            break
        except Exception as e:
            if i == max_retries - 1:
                raise
            time.sleep(1)
    
    db.install_all_labels()


def pytest_sessionfinish(session, exitstatus):
    """Stop container after all tests."""
    global _neo4j_container
    if _neo4j_container:
        _neo4j_container.stop()


@pytest.fixture(scope="session")
def neo4j_db():
    """Ensure Neo4j is connected for tests"""
    # The connection is already configured in pytest_sessionstart
    from neomodel import db
    return db


@pytest.fixture(autouse=True, scope="function")
def clean_database(request, neo4j_db):
    """Clean the database before each test"""
    # Only run for integration tests
    if "integration" not in [m.name for m in request.node.iter_markers()]:
        yield
        return
        
    try:
        # Clear all nodes before each test
        neo4j_db.cypher_query("MATCH (n) DETACH DELETE n")
    except Exception as e:
        # If database is not ready, it will fail but that's ok
        pass
    yield
    try:
        # Optionally clean after test as well
        neo4j_db.cypher_query("MATCH (n) DETACH DELETE n")
    except Exception:
        pass


@pytest.fixture
def mock_llm():
    """Mock LLM that returns predictable summaries"""
    mock = MagicMock()

    def predict(user_prompt, batch_size=1, max_length=512):
        # Return a simple summary based on the prompt
        return {"summary_text": SUMMARY_TEXT}

    mock.predict = predict
    return mock


@pytest.fixture
def mock_embedder():
    """Mock embedder that returns predictable embeddings"""
    mock = MagicMock()
    
    # Add model_card_data attribute
    mock.model_card_data = MagicMock()
    mock.model_card_data.model_name = "test-embedder-model"

    def encode(texts, batch_size=32, show_progress_bar=True):
        return NP_EMBEDDING

    mock.encode = encode
    return mock


@pytest.fixture
def mock_chunker():
    """Mock chunker that splits text into simple chunks"""
    
    call_count = 0

    def chunker(text):
        nonlocal call_count
        # Return unique chunks for each document to avoid idempotency collisions
        base = call_count * 5
        call_count += 1
        return [f"chunk_{base+1}", f"chunk_{base+2}", f"chunk_{base+3}", f"chunk_{base+4}", f"chunk_{base+5}"]

    return chunker
