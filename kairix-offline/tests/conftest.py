"""Root conftest.py file to ensure pytest picks up plugins."""
import os

# Load the integration plugin through pytest mechanisms
if os.environ.get('TESTING') == '1':
    pytest_plugins = ["tests.integration.conftest"]
