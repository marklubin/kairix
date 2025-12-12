"""Configuration for UI tests."""

import sys
from pathlib import Path

import pytest

# Add kairix-ui-testing to path if not installed as package
ui_testing_path = Path(__file__).parent.parent.parent.parent / "kairix-ui-testing" / "src"
if ui_testing_path.exists() and str(ui_testing_path) not in sys.path:
    sys.path.insert(0, str(ui_testing_path))

# Import UI testing fixtures and configuration
from kairix_ui_testing.fixtures import patch_memory_pipeline  # noqa: F401, E402


# Ensure test data directory exists
@pytest.fixture(scope="session", autouse=True)
def setup_test_data():
    """Create test data for UI tests."""
    test_data_dir = Path("test_data")
    test_data_dir.mkdir(exist_ok=True)

    # Create test JSON file
    test_file = test_data_dir / "test-convos.json"
    if not test_file.exists():
        import json
        test_data = {
            "conversations": [{
                "id": "test-1",
                "title": "Test Conversation",
                "create_time": 1704067200,
                "mapping": {
                    "msg1": {
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": ["Test message"]},
                            "create_time": 1704067200
                        }
                    }
                }
            }]
        }
        with open(test_file, "w") as f:
            json.dump(test_data, f, indent=2)
