"""UI tests for cross-tab functionality and general UI behavior."""

import pytest
from playwright.sync_api import Page, expect
import time

from kairix_ui_testing.core.ui_test_base import MemoryPipelineUITest
from kairix_ui_testing.test_scenarios import TestScenarios


class TestCrossTabBehavior(MemoryPipelineUITest):
    """Test interactions between tabs and general UI behavior."""
    
    test_config = TestScenarios.default()
    
    def test_tab_switching(self, ui_page: Page):
        """Test Case 3.1: Test tab navigation."""
        # Verify initial state - Import tab should be active
        import_tab = ui_page.locator(self.SELECTORS["import_tab"])
        synthesis_tab = ui_page.locator(self.SELECTORS["synthesis_tab"])
        
        # Check that import content is visible initially
        import_output = ui_page.locator(self.SELECTORS["import_output"])
        expect(import_output).to_be_visible()
        
        # Switch to synthesis tab
        synthesis_tab.click()
        time.sleep(0.2)
        
        # Synthesis content should be visible, import hidden
        synthesis_output = ui_page.locator(self.SELECTORS["synthesis_output"])
        expect(synthesis_output).to_be_visible()
        # Note: Gradio hides non-active tab content
        
        # Run an operation in synthesis tab
        ui_page.fill(self.SELECTORS["agent_name_input"], "TabTest")
        
        # Switch back to import tab
        import_tab.click()
        time.sleep(0.2)
        
        # Import content should be visible again
        expect(import_output).to_be_visible()
        
        # Switch back to synthesis - input should still have our value
        synthesis_tab.click()
        agent_value = ui_page.locator(self.SELECTORS["agent_name_input"]).input_value()
        assert agent_value == "TabTest", "Tab content should persist"
        
        # Rapid tab switching shouldn't cause issues
        for _ in range(5):
            import_tab.click()
            synthesis_tab.click()
        
        # UI should still be functional
        expect(synthesis_output).to_be_visible()
    
    def test_simultaneous_operations_ui(self, ui_page: Page):
        """Test Case 3.2: Test UI during concurrent operations."""
        # Start import operation
        ui_page.click(self.SELECTORS["import_tab"])
        ui_page.click(self.SELECTORS["import_button"])
        
        # Immediately switch to synthesis tab
        time.sleep(0.2)  # Let import start
        ui_page.click(self.SELECTORS["synthesis_tab"])
        
        # Synthesis UI should be responsive
        agent_input = ui_page.locator(self.SELECTORS["agent_name_input"])
        agent_input.fill("ConcurrentTest")
        assert agent_input.input_value() == "ConcurrentTest"
        
        # Try to start synthesis (should work independently)
        ui_page.fill(self.SELECTORS["run_id_input"], "concurrent-123")
        synthesis_button = ui_page.locator(self.SELECTORS["synthesis_button"])
        expect(synthesis_button).to_be_enabled()
        synthesis_button.click()
        
        # Switch back to import tab
        time.sleep(0.5)
        ui_page.click(self.SELECTORS["import_tab"])
        
        # Import should still be running/completed
        import_output = ui_page.locator(self.SELECTORS["import_output"]).input_value()
        assert len(import_output) > 0, "Import should have output"
        
        # Check synthesis result
        ui_page.click(self.SELECTORS["synthesis_tab"])
        synthesis_output = ui_page.locator(self.SELECTORS["synthesis_output"]).input_value()
        # Will show "no data imported" since import wasn't complete when synthesis started
        assert len(synthesis_output) > 0, "Synthesis should have output"
    
    def test_page_refresh_ui_state(self, ui_page: Page):
        """Test Case 3.5: Test UI after browser refresh."""
        # Perform some operations first
        ui_page.click(self.SELECTORS["import_button"])
        self.wait_for_streaming_complete(ui_page, self.SELECTORS["import_output"])
        
        # Switch to synthesis and fill fields
        ui_page.click(self.SELECTORS["synthesis_tab"])
        ui_page.fill(self.SELECTORS["agent_name_input"], "BeforeRefresh")
        ui_page.fill(self.SELECTORS["run_id_input"], "refresh-test")
        
        # Refresh the page
        ui_page.reload()
        
        # Wait for UI to load
        ui_page.wait_for_selector(self.SELECTORS["app_title"])
        
        # Verify UI returns to initial state
        # Import tab should be active (first tab)
        import_output = ui_page.locator(self.SELECTORS["import_output"])
        expect(import_output).to_be_visible()
        
        # Output areas should be cleared
        assert import_output.input_value() == "", "Import output should be cleared"
        
        # Switch to synthesis tab
        ui_page.click(self.SELECTORS["synthesis_tab"])
        
        # Fields should be empty
        agent_input = ui_page.locator(self.SELECTORS["agent_name_input"])
        run_id_input = ui_page.locator(self.SELECTORS["run_id_input"])
        synthesis_output = ui_page.locator(self.SELECTORS["synthesis_output"])
        
        assert agent_input.input_value() == "", "Agent name should be cleared"
        assert run_id_input.input_value() == "", "Run ID should be cleared"
        assert synthesis_output.input_value() == "", "Synthesis output should be cleared"
        
        # FileExplorer should show default
        ui_page.click(self.SELECTORS["import_tab"])
        # Default file should be selected again
        file_value = ui_page.locator(".gradio-fileexplorer").get_attribute("value")
        assert file_value == "test-convos.json", "Should restore default file selection"


class TestUIResponsiveness(MemoryPipelineUITest):
    """Test UI responsiveness and visual aspects."""
    
    test_config = TestScenarios.default()
    
    def test_window_resize_behavior(self, ui_page: Page):
        """Test Case 3.3: Test responsive layout."""
        # Get initial viewport size
        viewport = ui_page.viewport_size
        
        # Test narrow window
        ui_page.set_viewport_size({"width": 800, "height": 600})
        time.sleep(0.5)
        
        # UI elements should still be accessible
        expect(ui_page.locator(self.SELECTORS["import_button"])).to_be_visible()
        expect(ui_page.locator(self.SELECTORS["import_output"])).to_be_visible()
        
        # Test wide window
        ui_page.set_viewport_size({"width": 1920, "height": 1080})
        time.sleep(0.5)
        
        # Layout should adapt
        expect(ui_page.locator(self.SELECTORS["import_button"])).to_be_visible()
        
        # Test very narrow (mobile-like)
        ui_page.set_viewport_size({"width": 400, "height": 800})
        time.sleep(0.5)
        
        # Critical elements should still be accessible
        expect(ui_page.locator(self.SELECTORS["app_title"])).to_be_visible()
        expect(ui_page.locator(self.SELECTORS["import_button"])).to_be_visible()
        
        # Restore original size
        if viewport:
            ui_page.set_viewport_size(viewport)
    
    def test_theme_rendering(self, ui_page: Page):
        """Test Case 3.4: Verify theme displays correctly."""
        # Check that title is visible
        title = ui_page.locator(self.SELECTORS["app_title"])
        expect(title).to_be_visible()
        assert title.inner_text() == "Kairix Memory Architecture Pipline"
        
        # Verify theme is applied (calm_seafoam theme)
        # Check that primary buttons have the theme color
        import_button = ui_page.locator(self.SELECTORS["import_button"])
        
        # Test hover state
        import_button.hover()
        time.sleep(0.2)  # Allow hover effect
        
        # Verify button is styled as primary
        button_classes = import_button.get_attribute("class")
        assert "primary" in button_classes, "Should have primary button styling"
        
        # Check tab styling
        import_tab = ui_page.locator(self.SELECTORS["import_tab"])
        synthesis_tab = ui_page.locator(self.SELECTORS["synthesis_tab"])
        
        expect(import_tab).to_be_visible()
        expect(synthesis_tab).to_be_visible()
        
        # Verify no console errors
        console_errors = []
        ui_page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)
        ui_page.reload()  # Trigger fresh load
        ui_page.wait_for_selector(self.SELECTORS["app_title"])
        time.sleep(1)
        
        assert len(console_errors) == 0, f"Should have no console errors, found: {console_errors}"


class TestUIComponents(MemoryPipelineUITest):
    """Test specific UI component behaviors."""
    
    test_config = TestScenarios.default()
    
    def test_textbox_line_configuration(self, ui_page: Page):
        """Verify textboxes have correct line configuration."""
        # Check import output textbox
        import_output = ui_page.locator(self.SELECTORS["import_output"])
        
        # Gradio sets rows attribute for line height
        output_elem = import_output.locator("textarea")
        rows = output_elem.get_attribute("rows")
        assert rows == "20", "Output textbox should have 20 lines"
        
        # Check synthesis output has same configuration
        ui_page.click(self.SELECTORS["synthesis_tab"])
        synthesis_output = ui_page.locator(self.SELECTORS["synthesis_output"])
        synthesis_elem = synthesis_output.locator("textarea")
        rows = synthesis_elem.get_attribute("rows")
        assert rows == "20", "Synthesis output should also have 20 lines"
    
    def test_placeholder_text(self, ui_page: Page):
        """Verify placeholder text in output areas."""
        # Check import output placeholder
        import_output = ui_page.locator(self.SELECTORS["import_output"])
        import_textarea = import_output.locator("textarea")
        placeholder = import_textarea.get_attribute("placeholder")
        assert "import output will be displayed" in placeholder.lower()
        
        # Check synthesis output placeholder
        ui_page.click(self.SELECTORS["synthesis_tab"])
        synthesis_output = ui_page.locator(self.SELECTORS["synthesis_output"])
        synthesis_textarea = synthesis_output.locator("textarea")
        placeholder = synthesis_textarea.get_attribute("placeholder")
        assert "summarizer output will be displayed" in placeholder.lower()