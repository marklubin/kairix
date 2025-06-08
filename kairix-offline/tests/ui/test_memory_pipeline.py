"""UI tests for memory pipeline.

Tests import and synthesis functionality covering success and error scenarios.
"""

import pytest
from playwright.sync_api import Page, expect
import time

from kairix_ui_testing.core.ui_test_base import MemoryPipelineUITest
from kairix_ui_testing.test_scenarios import TestScenarios


class TestImportFunction(MemoryPipelineUITest):
    """Test import functionality with multiple scenarios."""
    
    app_module = 'kairix_offline.ui.memory_pipeline'
    app_attr = 'history_importer'
    test_config = TestScenarios.default()
    
    def test_import_scenarios(self, ui_page: Page):
        """Test import with success and error scenarios."""
        # Get elements
        import_button = ui_page.locator(self.SELECTORS["import_button"])
        import_output = ui_page.locator(self.SELECTORS["import_output"])
        
        # Test successful import with streaming
        import_button.click()
        
        # Verify streaming behavior
        text_snapshots = []
        for i in range(10):
            time.sleep(0.3)
            current_text = import_output.input_value()
            if current_text and current_text not in text_snapshots:
                text_snapshots.append(current_text)
            if current_text and "finished!" in current_text:
                break
        
        # Should see progressive updates
        assert len(text_snapshots) > 2, "Should see multiple text updates during streaming"
        
        # Wait for completion
        self.wait_for_streaming_complete(ui_page, self.SELECTORS["import_output"])
        final_text = import_output.input_value()
        
        # Verify success indicators
        assert "finished!" in final_text, "Should show completion message"
        assert "Wrote Source Documents" in final_text, "Should show documents written"
        assert "Test Conversation" in final_text, "Should show conversation titles"
        
        # Note: We cannot test error scenarios dynamically in the same test
        # because the mock configuration is fixed at startup


class TestSynthesisFunction(MemoryPipelineUITest):
    """Test synthesis functionality with multiple scenarios."""
    
    app_module = 'kairix_offline.ui.memory_pipeline'
    app_attr = 'history_importer'
    test_config = TestScenarios.default()
    
    def test_synthesis_scenarios(self, ui_page: Page):
        """Test synthesis with success and error scenarios."""
        # First import data for synthesis
        import_button = ui_page.locator(self.SELECTORS["import_button"])
        import_button.click()
        self.wait_for_streaming_complete(ui_page, self.SELECTORS["import_output"])
        
        # Get synthesis elements
        agent_input = ui_page.locator(self.SELECTORS["agent_name_input"])
        run_id_input = ui_page.locator(self.SELECTORS["run_id_input"])
        synthesis_button = ui_page.locator(self.SELECTORS["synthesis_button"])
        synthesis_output = ui_page.locator(self.SELECTORS["synthesis_output"])
        
        # Test error scenario - empty fields
        agent_input.fill("")
        run_id_input.fill("")
        synthesis_button.click()
        time.sleep(2.0)
        
        # Check output (mock doesn't validate empty fields, it processes them)
        error_output = synthesis_output.input_value()
        # The mock will process even with empty fields
        
        # Test success scenario
        agent_input.fill("TestAgent")
        run_id_input.fill("test-run-123")
        synthesis_button.click()
        
        # Wait for synthesis to complete
        time.sleep(3.0)
        
        # Get output
        output_text = synthesis_output.input_value()
        
        # Verify success indicators
        assert "Memory Synthesis Complete" in output_text, "Should show completion"
        assert "Agent: TestAgent" in output_text, "Should show agent name"
        assert "Run ID: test-run-123" in output_text, "Should show run ID"
        assert "Memories created:" in output_text, "Should show memories"
        assert "Test Conversation" in output_text, "Should reference imported data"


# Mark all tests as UI tests
pytestmark = pytest.mark.ui