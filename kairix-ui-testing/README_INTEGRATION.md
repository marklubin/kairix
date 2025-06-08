# Integrating Kairix UI Testing Framework

This document explains how to use the kairix-ui-testing framework in your package (e.g., kairix-offline).

## Setup

1. Add kairix-ui-testing as a dev dependency in your `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "kairix-ui-testing @ {root:uri}/../kairix-ui-testing",
    # ... other dev dependencies
]
```

2. Install with dev dependencies:

```bash
uv sync --dev
```

## Configuration

### 1. Update pytest configuration

Add to your `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "ui: UI tests that require browser automation",
]
testpaths = ["tests"]
# Add the plugin
plugins = ["kairix_ui_testing.pytest_plugin"]
```

### 2. Create UI test directory

```bash
mkdir -p tests/ui
```

### 3. Create a conftest.py for UI tests

Create `tests/ui/conftest.py`:

```python
"""Configuration for UI tests."""

import pytest
import sys
from pathlib import Path

# Import UI testing fixtures
pytest_plugins = ["kairix_ui_testing.fixtures"]

# Ensure the package is in path
package_root = Path(__file__).parent.parent.parent
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))
```

### 4. Create test files that import test cases

Create `tests/ui/test_memory_pipeline.py`:

```python
"""UI tests for memory pipeline."""

# Import the test classes from kairix-ui-testing
from kairix_ui_testing.test_cases.memory_pipeline import (
    TestImportTabStreaming,
    TestImportTabFileHandling,
    TestImportTabScrolling,
    TestImportTabErrors,
    TestSynthesisTabBasic,
    TestSynthesisTabValidation,
    TestSynthesisTabErrors,
    TestCrossTabBehavior,
    TestUIResponsiveness,
    TestUIComponents,
)

# Set the app location for all test classes
for test_class in [
    TestImportTabStreaming,
    TestImportTabFileHandling,
    TestImportTabScrolling,
    TestImportTabErrors,
    TestSynthesisTabBasic,
    TestSynthesisTabValidation,
    TestSynthesisTabErrors,
    TestCrossTabBehavior,
    TestUIResponsiveness,
    TestUIComponents,
]:
    test_class.app_module = 'kairix_offline.ui.memory_pipeline'
    test_class.app_attr = 'history_importer'
```

## Running UI Tests

```bash
# Run all UI tests
pytest tests/ui -m ui

# Run UI tests in headless mode
pytest tests/ui -m ui --ui-headless

# Run specific UI test class
pytest tests/ui/test_memory_pipeline.py::TestImportTabStreaming -v

# Run with visible browser (default)
pytest tests/ui -m ui --headed

# Generate HTML report
pytest tests/ui -m ui --html=reports/ui-test-report.html
```

## Makefile Integration

Add to your `Makefile`:

```makefile
# UI Testing
test-ui:
	uv run pytest tests/ui -m ui -v

test-ui-headless:
	uv run pytest tests/ui -m ui --ui-headless -v

test-ui-debug:
	PWDEBUG=1 uv run pytest tests/ui -m ui -s

# Install UI test dependencies
install-ui-test:
	uv sync --dev
	uv run playwright install firefox
```

## Customizing Test Scenarios

You can override test configurations in your test file:

```python
from kairix_ui_testing.test_cases.memory_pipeline import TestImportTabStreaming
from kairix_ui_testing.test_scenarios import TestScenarios

# Create a custom configuration
class TestImportWithCustomConfig(TestImportTabStreaming):
    app_module = 'kairix_offline.ui.memory_pipeline'
    app_attr = 'history_importer'
    
    # Override the test configuration
    test_config = {
        **TestScenarios.default(),
        'mock_conversation_count': 100,
        'import_delay': 0.1,
    }
```

## Writing Custom UI Tests

You can also write your own UI tests using the base class:

```python
from kairix_ui_testing.core.ui_test_base import MemoryPipelineUITest
from playwright.sync_api import Page

class TestCustomUI(MemoryPipelineUITest):
    app_module = 'kairix_offline.ui.my_custom_ui'
    app_attr = 'my_gradio_app'
    
    def test_custom_behavior(self, ui_page: Page):
        """Test custom UI behavior."""
        # Use helper methods from base class
        self.assert_element_visible(ui_page, "button")
        ui_page.click("button")
        
        # Wait for results
        self.wait_for_streaming_complete(ui_page, "textarea")
        
        # Check output
        output = self.get_output_text(ui_page, "textarea")
        assert "expected text" in output
```

## Troubleshooting

### Import Errors
- Make sure kairix-ui-testing is installed: `uv sync --dev`
- Check that the pytest plugin is loaded: `pytest --trace-config`

### Browser Issues
- Install Firefox: `uv run playwright install firefox`
- For headless issues, try: `pytest --headed`

### Test Discovery
- Ensure test files start with `test_`
- Check markers: `pytest --markers | grep ui`

### Server Port Conflicts
- Use different port: `pytest --ui-port 7863`