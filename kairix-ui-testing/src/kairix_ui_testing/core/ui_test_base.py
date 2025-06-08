"""Base class for UI tests with Playwright integration."""

import pytest
from playwright.sync_api import Page, expect
from typing import Optional, Dict, Any
import time
from pathlib import Path

from ..test_scenarios import TestScenarios


class MemoryPipelineUITest:
    """Base class for memory pipeline UI tests."""
    
    # Default test configuration
    test_config: Dict[str, Any] = TestScenarios.default()
    
    # UI element selectors
    SELECTORS = {
        # Import section
        "import_section": "text=ChatGPT History Importer",
        "file_explorer": "div[data-testid='fileexplorer']",  # Gradio uses data-testid
        "import_button": "button:has-text('Start') >> nth=0",
        "import_output": "textarea[placeholder*='import output']",
        
        # Synthesis section
        "synthesis_section": "text=Chunked Summary Memory Synth",
        # The textareas with no placeholder are Agent Name and Run ID (in order)
        "agent_name_input": "textarea >> nth=1",  # Second textarea (after import output)
        "run_id_input": "textarea >> nth=2",      # Third textarea
        "synthesis_button": "button:has-text('Start') >> nth=1",
        "synthesis_output": "textarea[placeholder*='summarizer output']",
        
        # General
        "app_title": "h1",
        
        # Legacy tab references (no actual tabs in UI)
        "import_tab": "text=ChatGPT History Importer",
        "synthesis_tab": "text=Chunked Summary Memory Synth",
    }
    
    @pytest.fixture(scope="class")
    def test_server(self):
        """Launch test UI server for the test class."""
        from .patched_server import patched_ui_server
        import random
        # These need to be set by the target package
        app_module = getattr(self, 'app_module', 'kairix_offline.ui.memory_pipeline')
        app_attr = getattr(self, 'app_attr', 'history_importer')
        
        # Use random port to avoid conflicts
        port = random.randint(7860, 7890)
        
        with patched_ui_server(app_module, app_attr, self.test_config, port=port) as url:
            yield url
        
    @pytest.fixture
    def ui_page(self, page: Page, test_server: str, patch_memory_pipeline):
        """Navigate to test UI and return page."""
        # Store the mock patches instance for tests to access
        self.mock_patches = patch_memory_pipeline
        
        page.goto(test_server)
        page.wait_for_selector(self.SELECTORS["app_title"])
        return page
    
    def wait_for_streaming_complete(self, page: Page, output_selector: str, timeout: int = 30):
        """Wait for streaming output to complete."""
        # Use locator instead of querySelector for better compatibility
        output_elem = page.locator(output_selector)
        
        # Wait for text to appear
        output_elem.wait_for(state="visible", timeout=timeout * 1000)
        page.wait_for_timeout(500)  # Initial delay
        
        # Wait for text to stop changing
        previous_length = 0
        stable_count = 0
        while stable_count < 3:  # Text unchanged for 3 checks
            current_text = output_elem.input_value()
            current_length = len(current_text)
            if current_length == previous_length:
                stable_count += 1
            else:
                stable_count = 0
            previous_length = current_length
            time.sleep(0.2)
    
    def get_output_text(self, page: Page, output_selector: str) -> str:
        """Get text from output textarea."""
        return page.locator(output_selector).input_value()
    
    def upload_test_file(self, page: Page, filename: str = "test-convos.json"):
        """Helper to select a file in FileExplorer."""
        # Click on the file in FileExplorer
        file_selector = f"text={filename}"
        page.click(file_selector)
        
    def fill_synthesis_inputs(self, page: Page, agent_name: str, run_id: str):
        """Helper to fill synthesis form inputs."""
        page.fill(self.SELECTORS["agent_name_input"], agent_name)
        page.fill(self.SELECTORS["run_id_input"], run_id)
    
    def assert_element_visible(self, page: Page, selector: str):
        """Assert that an element is visible."""
        expect(page.locator(selector)).to_be_visible()
    
    def assert_button_enabled(self, page: Page, selector: str):
        """Assert that a button is enabled."""
        expect(page.locator(selector)).to_be_enabled()
    
    def assert_button_disabled(self, page: Page, selector: str):
        """Assert that a button is disabled."""
        expect(page.locator(selector)).to_be_disabled()
    
    def take_screenshot_on_failure(self, page: Page, test_name: str):
        """Take screenshot for debugging."""
        screenshot_dir = Path("screenshots")
        screenshot_dir.mkdir(exist_ok=True)
        page.screenshot(path=str(screenshot_dir / f"{test_name}_failure.png"))
    
    def get_scroll_position(self, page: Page, selector: str) -> Dict[str, int]:
        """Get current scroll position of element."""
        elem = page.locator(selector)
        # Get the actual textarea element within the component
        textarea = elem.locator("textarea").first if elem.locator("textarea").count() else elem
        return textarea.evaluate("""
            elem => ({ scrollTop: elem.scrollTop, scrollHeight: elem.scrollHeight, clientHeight: elem.clientHeight })
        """)
    
    def scroll_element(self, page: Page, selector: str, position: str = "bottom"):
        """Scroll element to specified position."""
        elem = page.locator(selector)
        textarea = elem.locator("textarea").first if elem.locator("textarea").count() else elem
        if position == "bottom":
            textarea.evaluate("elem => elem.scrollTop = elem.scrollHeight")
        elif position == "top":
            textarea.evaluate("elem => elem.scrollTop = 0")
        elif isinstance(position, int):
            page.evaluate(f"document.querySelector('{selector}').scrollTop = {position}")