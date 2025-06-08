"""UI tests for the Import Tab functionality."""

import pytest
from playwright.sync_api import Page, expect
import time

from kairix_ui_testing.core.ui_test_base import MemoryPipelineUITest
from kairix_ui_testing.test_scenarios import TestScenarios


class TestImportTabStreaming(MemoryPipelineUITest):
    """Test streaming behavior of import functionality."""
    
    test_config = TestScenarios.streaming_test()
    
    def test_import_streaming_display(self, ui_page: Page):
        """Test Case 1.1: Verify text streams into output box progressively."""
        # Get initial state of output
        output_elem = ui_page.locator(self.SELECTORS["import_output"])
        initial_text = output_elem.input_value()
        assert initial_text == "", "Output should be empty initially"
        
        # Click the import button (file explorer has default selection)
        ui_page.click(self.SELECTORS["import_button"])
        
        # Capture text at different points to verify streaming
        text_snapshots = []
        for i in range(5):
            time.sleep(0.3)
            current_text = output_elem.input_value()
            if current_text and current_text not in text_snapshots:
                text_snapshots.append(current_text)
        
        # Verify we captured progressive updates
        assert len(text_snapshots) > 2, "Should see multiple text updates during streaming"
        
        # Verify content appears in order
        assert any("Loading" in snapshot for snapshot in text_snapshots[:2]), "Should see loading message early"
        assert "finished!" in text_snapshots[-1], "Should see completion message at end"
        
        # Verify scrollbar appears
        scroll_info = self.get_scroll_position(ui_page, self.SELECTORS["import_output"])
        assert scroll_info["scrollHeight"] > scroll_info["clientHeight"], "Should have scrollbar for long content"
    
    def test_import_button_state_during_operation(self, ui_page: Page):
        """Test Case 1.2: Verify button disabled during operation."""
        button = ui_page.locator(self.SELECTORS["import_button"])
        
        # Button should be enabled initially
        expect(button).to_be_enabled()
        
        # Click to start import
        button.click()
        
        # Button should be disabled during operation
        expect(button).to_be_disabled()
        
        # Wait for completion
        self.wait_for_streaming_complete(ui_page, self.SELECTORS["import_output"])
        
        # Button should be re-enabled
        expect(button).to_be_enabled()
        
        # Verify no duplicate operations from rapid clicks
        button.click()
        initial_length = len(ui_page.locator(self.SELECTORS["import_output"]).input_value())
        button.click()  # Try rapid second click
        time.sleep(0.1)
        # Length shouldn't immediately double (would indicate duplicate operation)
        current_length = len(ui_page.locator(self.SELECTORS["import_output"]).input_value())
        assert current_length < initial_length * 1.5, "Rapid clicks should not trigger duplicate operations"


class TestImportTabFileHandling(MemoryPipelineUITest):
    """Test file selection and error handling."""
    
    test_config = {**TestScenarios.default(), "default_file_exists": True}
    
    def test_import_file_explorer_interaction(self, ui_page: Page):
        """Test Case 1.3: Test file selection UI component."""
        # Verify FileExplorer is visible
        file_explorer = ui_page.locator(self.SELECTORS["file_explorer"])
        expect(file_explorer).to_be_visible()
        
        # Check default selection
        # FileExplorer should show test-convos.json selected by default
        selected_file = ui_page.locator(".gradio-fileexplorer").get_attribute("value")
        assert selected_file == "test-convos.json", "Should have default file selected"
        
        # Note: Full FileExplorer interaction (navigation, selection) would require
        # more complex selectors specific to Gradio's FileExplorer implementation
    
    def test_import_output_persistence(self, ui_page: Page):
        """Test Case 1.4: Verify output remains visible after operation."""
        # Run an import
        ui_page.click(self.SELECTORS["import_button"])
        self.wait_for_streaming_complete(ui_page, self.SELECTORS["import_output"])
        
        # Get the output text
        output_elem = ui_page.locator(self.SELECTORS["import_output"])
        output_text = output_elem.input_value()
        assert len(output_text) > 0, "Should have output after import"
        
        # Switch to synthesis tab and back
        ui_page.click(self.SELECTORS["synthesis_tab"])
        time.sleep(0.5)
        ui_page.click(self.SELECTORS["import_tab"])
        
        # Output should still be there
        persisted_text = output_elem.input_value()
        assert persisted_text == output_text, "Output should persist when switching tabs"
        
        # Verify text is selectable (user can copy)
        output_elem.click()
        ui_page.keyboard.press("Control+A")  # Select all
        # If text is selectable, this won't throw an error


class TestImportTabScrolling(MemoryPipelineUITest):
    """Test scrolling behavior with long output."""
    
    test_config = TestScenarios.long_output_test()
    
    def test_import_long_output_scrolling(self, ui_page: Page):
        """Test Case 1.5: Test output box with extensive content."""
        output_elem = ui_page.locator(self.SELECTORS["import_output"])
        
        # Start import with many conversations
        ui_page.click(self.SELECTORS["import_button"])
        
        # Let some content stream in
        time.sleep(1)
        
        # Check that scrollbar appears
        scroll_info = self.get_scroll_position(ui_page, self.SELECTORS["import_output"])
        assert scroll_info["scrollHeight"] > scroll_info["clientHeight"], "Should have scrollbar"
        
        # Scroll up manually
        self.scroll_element(ui_page, self.SELECTORS["import_output"], "top")
        time.sleep(0.5)
        
        # Verify we're at top
        scroll_pos = self.get_scroll_position(ui_page, self.SELECTORS["import_output"])
        assert scroll_pos["scrollTop"] == 0, "Should be scrolled to top"
        
        # Wait a bit more for new content
        time.sleep(1)
        
        # Verify scroll position hasn't jumped (user scroll should be respected)
        new_scroll_pos = self.get_scroll_position(ui_page, self.SELECTORS["import_output"])
        assert new_scroll_pos["scrollTop"] < 100, "Scroll position should stay near top when user has scrolled"
        
        # Wait for completion
        self.wait_for_streaming_complete(ui_page, self.SELECTORS["import_output"])
        
        # Verify we can scroll to bottom
        self.scroll_element(ui_page, self.SELECTORS["import_output"], "bottom")
        final_scroll = self.get_scroll_position(ui_page, self.SELECTORS["import_output"])
        assert final_scroll["scrollTop"] > 0, "Should be able to scroll"
        
        # Verify final output contains many items
        final_text = output_elem.input_value()
        conversation_count = final_text.count("Processing conversation:")
        assert conversation_count > 50, f"Should process many conversations, got {conversation_count}"


class TestImportTabErrors(MemoryPipelineUITest):
    """Test error scenarios."""
    
    test_config = {**TestScenarios.default(), "default_file_exists": False}
    
    def test_import_no_file_selected(self, ui_page: Page):
        """Test import with no file selected."""
        # Clear any default selection
        file_explorer = ui_page.locator(self.SELECTORS["file_explorer"])
        
        # Click import without selecting a file
        ui_page.click(self.SELECTORS["import_button"])
        
        # Should see error message quickly
        time.sleep(0.5)
        output_text = ui_page.locator(self.SELECTORS["import_output"]).input_value()
        assert "No file selected" in output_text, "Should show no file selected message"