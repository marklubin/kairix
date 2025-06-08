"""Base test class for all Kairix UI tests."""

import pytest
from playwright.sync_api import Page, BrowserContext
from pathlib import Path
from datetime import datetime
from ..config.settings import TestConfig


class KairixUITest:
    """Base class for all Kairix UI tests - Firefox only."""
    
    config = TestConfig()
    
    @pytest.fixture(autouse=True)
    def setup_firefox(self, page: Page, browser_context: BrowserContext):
        """Firefox-specific setup."""
        self.page = page
        self.context = browser_context
        
        # Firefox-specific configurations
        self.page.set_default_timeout(self.config.default_timeout * 1000)
        
        # Enable Firefox developer tools if needed
        if not self.config.headless:
            self.context.set_extra_http_headers({
                "User-Agent": "KairixUITest/1.0 (Firefox)"
            })
    
    def setup_method(self, method):
        """Setup before each test method."""
        self.test_name = method.__name__
        self.screenshots = []
        
    def teardown_method(self, method):
        """Cleanup after each test method."""
        # Take screenshot on failure
        if hasattr(self, '_outcome') and self._outcome.failed:
            self.take_screenshot("failure")
    
    def take_screenshot(self, name: str):
        """Take a timestamped screenshot."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.test_name}_{name}_{timestamp}.png"
        filepath = self.config.screenshot_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        self.page.screenshot(path=str(filepath))
        self.screenshots.append(filepath)
        return filepath
    
    def wait_for_element(self, selector: str, timeout: int = None):
        """Wait for element with smart retry."""
        timeout = timeout or self.config.default_timeout
        return self.page.wait_for_selector(selector, timeout=timeout * 1000)
    
    def safe_click(self, selector: str):
        """Click element with wait."""
        element = self.wait_for_element(selector)
        element.click()
    
    def safe_fill(self, selector: str, value: str):
        """Fill input with wait."""
        element = self.wait_for_element(selector)
        element.fill(value)