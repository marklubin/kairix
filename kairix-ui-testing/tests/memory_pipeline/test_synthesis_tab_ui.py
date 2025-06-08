"""UI tests for the Synthesis Tab functionality."""

import pytest
from playwright.sync_api import Page, expect
import time

from kairix_ui_testing.core.ui_test_base import MemoryPipelineUITest
from kairix_ui_testing.test_scenarios import TestScenarios


class TestSynthesisTabBasic(MemoryPipelineUITest):
    """Test basic synthesis tab functionality."""
    
    test_config = TestScenarios.default()
    
    def test_synthesis_input_fields(self, ui_page: Page):
        """Test Case 2.1: Test text input interactions."""
        # Navigate to synthesis tab
        ui_page.click(self.SELECTORS["synthesis_tab"])
        
        # Verify input fields are visible
        agent_input = ui_page.locator(self.SELECTORS["agent_name_input"])
        run_id_input = ui_page.locator(self.SELECTORS["run_id_input"])
        
        expect(agent_input).to_be_visible()
        expect(run_id_input).to_be_visible()
        
        # Verify placeholder text
        assert agent_input.get_attribute("placeholder") == "Enter agent name"
        assert run_id_input.get_attribute("placeholder") == "Enter run ID"
        
        # Test typing in fields
        agent_input.fill("TestAgent")
        assert agent_input.input_value() == "TestAgent"
        
        # Test tab navigation
        agent_input.click()
        ui_page.keyboard.press("Tab")
        # Run ID field should now be focused
        assert ui_page.evaluate("document.activeElement.placeholder") == "Enter run ID"
        
        # Type in run ID field
        run_id_input.fill("test-run-123")
        assert run_id_input.input_value() == "test-run-123"
        
        # Test clearing and re-entering
        agent_input.fill("")
        assert agent_input.input_value() == ""
        agent_input.fill("NewAgent")
        assert agent_input.input_value() == "NewAgent"
    
    def test_synthesis_output_appears_at_once(self, ui_page: Page):
        """Test Case 2.2: Verify batch output behavior (not streaming)."""
        # First, run an import to have data
        ui_page.click(self.SELECTORS["import_tab"])
        ui_page.click(self.SELECTORS["import_button"])
        self.wait_for_streaming_complete(ui_page, self.SELECTORS["import_output"])
        
        # Navigate to synthesis tab
        ui_page.click(self.SELECTORS["synthesis_tab"])
        
        # Fill in fields
        ui_page.fill(self.SELECTORS["agent_name_input"], "TestAgent")
        ui_page.fill(self.SELECTORS["run_id_input"], "test-123")
        
        # Get output element
        output_elem = ui_page.locator(self.SELECTORS["synthesis_output"])
        initial_value = output_elem.input_value()
        assert initial_value == "", "Output should be empty initially"
        
        # Click synthesis button
        ui_page.click(self.SELECTORS["synthesis_button"])
        
        # Check multiple times during processing
        text_during_processing = []
        for i in range(5):
            time.sleep(0.3)
            current_text = output_elem.input_value()
            text_during_processing.append(current_text)
        
        # All intermediate checks should show empty (no streaming)
        empty_count = sum(1 for text in text_during_processing[:4] if text == "")
        assert empty_count >= 3, "Output should stay empty during processing (not streaming)"
        
        # Wait for completion
        time.sleep(2)
        final_text = output_elem.input_value()
        
        # Verify output appears all at once
        assert len(final_text) > 0, "Should have output after completion"
        assert "Memory synthesis complete!" in final_text, "Should show completion message"
        assert "TestAgent" in final_text, "Should include agent name"
        assert "test-123" in final_text, "Should include run ID"


class TestSynthesisTabValidation(MemoryPipelineUITest):
    """Test synthesis tab validation and edge cases."""
    
    test_config = TestScenarios.default()
    
    def test_synthesis_button_with_empty_fields(self, ui_page: Page):
        """Test Case 2.3: Test button behavior with empty inputs."""
        # Navigate to synthesis tab
        ui_page.click(self.SELECTORS["synthesis_tab"])
        
        # Verify button is clickable even with empty fields
        synthesis_button = ui_page.locator(self.SELECTORS["synthesis_button"])
        expect(synthesis_button).to_be_enabled()
        
        # First run import so we have data
        ui_page.click(self.SELECTORS["import_tab"])
        ui_page.click(self.SELECTORS["import_button"])
        self.wait_for_streaming_complete(ui_page, self.SELECTORS["import_output"])
        
        # Go back to synthesis
        ui_page.click(self.SELECTORS["synthesis_tab"])
        
        # Click with empty fields
        synthesis_button.click()
        
        # Wait for response
        time.sleep(2)
        output_text = ui_page.locator(self.SELECTORS["synthesis_output"]).input_value()
        
        # Should still process but show "Unknown" for empty fields
        assert len(output_text) > 0, "Should produce output even with empty fields"
        assert "Unknown" in output_text, "Should show 'Unknown' for empty fields"
    
    def test_synthesis_field_values_during_operation(self, ui_page: Page):
        """Test Case 2.4: Verify input fields during processing."""
        # Setup: Import data first
        ui_page.click(self.SELECTORS["import_tab"])
        ui_page.click(self.SELECTORS["import_button"])
        self.wait_for_streaming_complete(ui_page, self.SELECTORS["import_output"])
        
        # Navigate to synthesis tab
        ui_page.click(self.SELECTORS["synthesis_tab"])
        
        # Fill fields
        agent_input = ui_page.locator(self.SELECTORS["agent_name_input"])
        run_id_input = ui_page.locator(self.SELECTORS["run_id_input"])
        
        agent_input.fill("OriginalAgent")
        run_id_input.fill("original-run")
        
        # Start synthesis
        ui_page.click(self.SELECTORS["synthesis_button"])
        
        # Try to edit fields during processing
        time.sleep(0.5)  # During processing
        agent_input.fill("ModifiedAgent")
        run_id_input.fill("modified-run")
        
        # Verify fields accept the new values
        assert agent_input.input_value() == "ModifiedAgent"
        assert run_id_input.input_value() == "modified-run"
        
        # Wait for completion
        time.sleep(2)
        output_text = ui_page.locator(self.SELECTORS["synthesis_output"]).input_value()
        
        # Output should show original values (not modified ones)
        assert "OriginalAgent" in output_text, "Should use original agent name"
        assert "original-run" in output_text, "Should use original run ID"
    
    def test_synthesis_output_formatting(self, ui_page: Page):
        """Test Case 2.5: Test text display formatting."""
        # Setup: Import data
        ui_page.click(self.SELECTORS["import_tab"])
        ui_page.click(self.SELECTORS["import_button"])
        self.wait_for_streaming_complete(ui_page, self.SELECTORS["import_output"])
        
        # Run synthesis
        ui_page.click(self.SELECTORS["synthesis_tab"])
        ui_page.fill(self.SELECTORS["agent_name_input"], "TestAgent")
        ui_page.fill(self.SELECTORS["run_id_input"], "format-test")
        ui_page.click(self.SELECTORS["synthesis_button"])
        
        # Wait for completion
        time.sleep(2.5)
        output_elem = ui_page.locator(self.SELECTORS["synthesis_output"])
        output_text = output_elem.input_value()
        
        # Verify formatting
        assert "✅" in output_text, "Should render checkmark emoji"
        assert "\n" in output_text, "Should have line breaks"
        assert output_text.count("\n") > 3, "Should have multiple lines"
        
        # Verify content structure
        assert "Split input into" in output_text, "Should show chunk info"
        assert "Memory synthesis complete!" in output_text, "Should show completion"
        assert "Total memory shards:" in output_text, "Should show statistics"
        
        # Verify the textarea preserves formatting
        lines = output_text.split("\n")
        assert any(line.strip() == "" for line in lines), "Should have empty lines for spacing"


class TestSynthesisTabErrors(MemoryPipelineUITest):
    """Test synthesis error scenarios."""
    
    test_config = TestScenarios.default()
    
    def test_synthesis_without_import(self, ui_page: Page):
        """Test synthesis without importing data first."""
        # Go directly to synthesis tab
        ui_page.click(self.SELECTORS["synthesis_tab"])
        
        # Fill fields and try to synthesize
        ui_page.fill(self.SELECTORS["agent_name_input"], "TestAgent")
        ui_page.fill(self.SELECTORS["run_id_input"], "test-run")
        ui_page.click(self.SELECTORS["synthesis_button"])
        
        # Should get error message quickly
        time.sleep(0.5)
        output_text = ui_page.locator(self.SELECTORS["synthesis_output"]).input_value()
        
        assert "❌" in output_text, "Should show error indicator"
        assert "No data imported" in output_text, "Should explain the error"
        assert "Please import ChatGPT export first" in output_text, "Should provide guidance"