"""pytest plugin to configure Neo4j before any imports."""
import os

# Remove all database-related environment variables before any imports
env_vars_to_remove = [
    'NEO4J_URL',
    'KAIRIX_DATABASE_URL',
    'DATABASE_URL'
]

for var in env_vars_to_remove:
    if var in os.environ:
        del os.environ[var]

# This runs before any test imports
def pytest_configure(config):
    """Configure test environment before collecting tests."""
    # Ensure database URLs are not set
    for var in env_vars_to_remove:
        if var in os.environ:
            del os.environ[var]