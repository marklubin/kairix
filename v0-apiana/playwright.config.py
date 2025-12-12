"""
Playwright configuration for UI automation tests.
"""

import os

# Test configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:7860")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
BROWSER_TIMEOUT = 30000  # 30 seconds
TEST_TIMEOUT = 120000    # 2 minutes

def pytest_configure(config):
    """Configure pytest for Playwright tests."""
    config.addinivalue_line(
        "markers", "ui_automation: marks tests as UI automation tests using Playwright"
    )

def pytest_playwright_page_goto(page, url, **kwargs):
    """Custom page goto handler."""
    return page.goto(url, wait_until="networkidle", **kwargs)

# Playwright browser configuration
BROWSER_CONFIG = {
    "headless": HEADLESS,
    "slow_mo": 100 if not HEADLESS else 0,  # Slow down for visual debugging
    "args": [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--disable-backgrounding-occluded-windows",
    ]
}

PAGE_CONFIG = {
    "viewport": {"width": 1280, "height": 720},
    "ignore_https_errors": True,
}

# Test data paths
TEST_DATA_DIR = "tests/fixtures"
SCREENSHOTS_DIR = "tests/ui_automation/screenshots"

# Ensure screenshot directory exists
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)