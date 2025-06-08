"""Pytest plugin for UI testing."""

import pytest


def pytest_configure(config):
    """Register the ui marker."""
    config.addinivalue_line(
        "markers", 
        "ui: mark test as a UI test that requires browser automation"
    )
    
    # Add browser options for UI tests
    if config.getoption("--browser", None) is None:
        config.option.browser = "firefox"
    if config.getoption("--browser-channel", None) is None:
        config.option.browser_channel = "firefox"
    if not hasattr(config.option, "headed"):
        config.option.headed = True


def pytest_collection_modifyitems(config, items):
    """Add ui marker to all UI test classes."""
    for item in items:
        # Check if this is a UI test based on class inheritance
        if hasattr(item, "cls"):
            cls = item.cls
            # Check if it inherits from MemoryPipelineUITest
            if cls and "MemoryPipelineUITest" in [base.__name__ for base in cls.__mro__]:
                item.add_marker(pytest.mark.ui)


def pytest_addoption(parser):
    """Add UI testing options."""
    parser.addoption(
        "--ui-port",
        action="store",
        default=7862,
        help="Port to run UI test server on"
    )
    parser.addoption(
        "--ui-headless",
        action="store_true",
        default=False,
        help="Run UI tests in headless mode"
    )