"""Example test structure showing how to use the test infrastructure."""

import pytest
from playwright.sync_api import Page
from kairix_ui_testing.core.ui_test_base import MemoryPipelineUITest
from kairix_ui_testing.test_scenarios import TestScenarios


class TestImportTabUI(MemoryPipelineUITest):
    """Example tests for the Import tab UI behavior."""
    
    # Configure this test class to use specific mock behavior
    test_config = TestScenarios.streaming_test()
    
    def test_example_structure(self, ui_page: Page):
        """Example test showing available methods and assertions."""
        
        # 1. Verify initial UI state
        self.assert_element_visible(ui_page, self.SELECTORS["app_title"])
        self.assert_element_visible(ui_page, self.SELECTORS["import_button"])
        
        # 2. Interact with UI elements
        self.upload_test_file(ui_page, "test-convos.json")
        ui_page.click(self.SELECTORS["import_button"])
        
        # 3. Wait for streaming to complete
        self.wait_for_streaming_complete(ui_page, self.SELECTORS["import_output"])
        
        # 4. Verify output
        output_text = self.get_output_text(ui_page, self.SELECTORS["import_output"])
        assert "Loading test-convos.json" in output_text
        assert "finished!" in output_text
        
        # 5. Check UI state after operation
        self.assert_button_enabled(ui_page, self.SELECTORS["import_button"])
        
        # 6. Test scrolling behavior
        scroll_info = self.get_scroll_position(ui_page, self.SELECTORS["import_output"])
        assert scroll_info["scrollHeight"] > scroll_info["clientHeight"], "Should have scrollbar"
        
    def test_different_scenario(self, ui_page: Page):
        """Example using a different test scenario."""
        # This test would use the streaming_test() configuration
        # defined at the class level
        pass


class TestErrorScenarios(MemoryPipelineUITest):
    """Example tests for error scenarios."""
    
    # Use error configuration for this test class
    test_config = TestScenarios.error_scenarios()
    
    def test_import_error_display(self, ui_page: Page):
        """Test that errors display properly."""
        # The mock is configured to fail imports
        self.upload_test_file(ui_page)
        ui_page.click(self.SELECTORS["import_button"])
        
        # Wait for error to appear
        self.wait_for_streaming_complete(ui_page, self.SELECTORS["import_output"])
        
        output = self.get_output_text(ui_page, self.SELECTORS["import_output"])
        assert "Database connection failed" in output


# You can also override configuration per test
def test_with_custom_config(page: Page):
    """Example of test with custom configuration."""
    custom_config = {
        "mock_conversation_count": 3,
        "import_should_fail": False,
        "summarize_delay": 0.5,
    }
    
    # This would need custom fixture to launch with specific config
    # Just showing the pattern here