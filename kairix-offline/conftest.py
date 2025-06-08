"""Root conftest for pytest configuration."""
import os
import sys

# Ensure we're using test configuration
os.environ['TESTING'] = '1'

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))