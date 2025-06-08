"""pytest plugin to configure Neo4j before any imports."""
import os

# Remove NEO4J_URL from environment before any imports
if 'NEO4J_URL' in os.environ:
    del os.environ['NEO4J_URL']

# This runs before any test imports
def pytest_configure(config):
    """Configure test environment before collecting tests."""
    # Ensure NEO4J_URL is not set
    if 'NEO4J_URL' in os.environ:
        del os.environ['NEO4J_URL']