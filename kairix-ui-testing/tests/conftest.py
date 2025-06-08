"""Pytest configuration for UI tests."""

import pytest
from playwright.sync_api import Page, BrowserContext
from pathlib import Path
import os
import sys
from dotenv import load_dotenv

# Add src to path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Load environment variables
load_dotenv()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure Firefox-specific context."""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
        # Firefox-specific settings
        "firefox_user_prefs": {
            "dom.webnotifications.enabled": False,
            "media.navigator.enabled": True,
            "media.navigator.video.enabled": True,
            "browser.download.folderList": 2,
            "browser.download.dir": str(Path.cwd() / "downloads"),
            "browser.helperApps.neverAsk.saveToDisk": "application/json,text/plain",
        }
    }


@pytest.fixture
def test_data_dir():
    """Provide test data directory path."""
    data_dir = Path("test_data")
    data_dir.mkdir(exist_ok=True)
    return data_dir


@pytest.fixture
def sample_chatgpt_export(test_data_dir):
    """Create a sample ChatGPT export file for testing."""
    sample_data = {
        "conversations": [
            {
                "id": "test-conv-1",
                "title": "Test Conversation 1",
                "create_time": 1704067200,
                "mapping": {
                    "msg1": {
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": ["Hello, this is a test"]},
                            "create_time": 1704067200
                        }
                    },
                    "msg2": {
                        "message": {
                            "author": {"role": "assistant"},
                            "content": {"parts": ["Hello! This is a test response."]},
                            "create_time": 1704067260
                        }
                    }
                }
            }
        ]
    }
    
    import json
    file_path = test_data_dir / "sample_export.json"
    with open(file_path, "w") as f:
        json.dump(sample_data, f, indent=2)
    
    return file_path


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test."""
    # Create necessary directories
    Path("screenshots").mkdir(exist_ok=True)
    Path("downloads").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)
    
    yield
    
    # Cleanup can be added here if needed


# Hook for test failure screenshots
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Take screenshot on test failure."""
    outcome = yield
    rep = outcome.get_result()
    
    if rep.when == "call" and rep.failed:
        # Access the test instance if it has a page
        if hasattr(item, "funcargs") and "page" in item.funcargs:
            page = item.funcargs["page"]
            screenshot_dir = Path("screenshots")
            screenshot_dir.mkdir(exist_ok=True)
            
            screenshot_path = screenshot_dir / f"{item.name}_failure.png"
            page.screenshot(path=str(screenshot_path))
            
            # Add screenshot to report
            if hasattr(rep, "extra"):
                rep.extra.append(("screenshot", str(screenshot_path)))


# Import test server utilities
from kairix_ui_testing.core.test_server import test_server, TestServer
from kairix_ui_testing.test_scenarios import TestScenarios


@pytest.fixture(scope="session")
def default_test_server():
    """Default test server for all tests."""
    with test_server(TestScenarios.default(), port=7862) as url:
        yield url


# Add kairix-offline dependencies to path
import sys
from pathlib import Path
offline_path = Path(__file__).parent.parent.parent / "kairix-offline" / "src"
if str(offline_path) not in sys.path:
    sys.path.insert(0, str(offline_path))