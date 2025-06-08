"""Base page object pattern implementation."""

from playwright.sync_api import Page
from typing import Optional
from ..config.settings import TestConfig


class BasePage:
    """Base page object with common functionality."""
    
    def __init__(self, page: Page, config: TestConfig = None):
        self.page = page
        self.config = config or TestConfig()
        
    def navigate_to(self, url: str):
        """Navigate to URL with retry logic."""
        self.page.goto(url, wait_until="networkidle")
        
    def wait_for_load(self):
        """Wait for page to be fully loaded."""
        self.page.wait_for_load_state("networkidle")
        # Firefox sometimes needs extra time
        self.page.wait_for_timeout(500)
        
    def get_element(self, selector: str, timeout: Optional[int] = None):
        """Get element with wait."""
        timeout = timeout or self.config.default_timeout
        return self.page.wait_for_selector(selector, timeout=timeout * 1000)
    
    def element_exists(self, selector: str) -> bool:
        """Check if element exists."""
        return self.page.locator(selector).count() > 0
    
    def get_text(self, selector: str) -> str:
        """Get text content of element."""
        element = self.get_element(selector)
        return element.text_content() or ""
    
    def click(self, selector: str):
        """Click element."""
        element = self.get_element(selector)
        element.click()
        
    def fill(self, selector: str, value: str):
        """Fill input field."""
        element = self.get_element(selector)
        element.fill(value)
        
    def upload_file(self, selector: str, file_path: str):
        """Upload file to file input."""
        element = self.get_element(selector)
        element.set_input_files(file_path)