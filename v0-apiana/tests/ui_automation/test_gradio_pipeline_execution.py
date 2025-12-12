"""
UI Automation Tests for Gradio Pipeline Execution

These tests use Playwright to simulate user interactions with the Gradio web interface,
testing the complete workflow from pipeline selection to execution and result verification.
"""

import pytest
import asyncio
import tempfile
import json
import time
from pathlib import Path
from playwright.sync_api import Page, expect
import threading
import subprocess
import signal
import os


# Global variable to track the Gradio server process
gradio_process = None
server_ready = False


class GradioServerManager:
    """Manages the Gradio server lifecycle for testing."""
    
    def __init__(self, host="127.0.0.1", port=7860):
        self.host = host
        self.port = port
        self.process = None
        self.ready = False
        
    def start_server(self):
        """Start the Gradio server in a subprocess."""
        import subprocess
        import sys
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        launch_script = project_root / "launch_gradio.py"
        
        # Start the Gradio server
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        self.process = subprocess.Popen([
            sys.executable, str(launch_script),
            "--host", self.host,
            "--port", str(self.port)
        ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to be ready
        max_wait = 30  # 30 seconds timeout
        for _ in range(max_wait):
            try:
                import requests
                response = requests.get(f"http://{self.host}:{self.port}")
                if response.status_code == 200:
                    self.ready = True
                    break
            except:
                pass
            time.sleep(1)
        
        if not self.ready:
            self.stop_server()
            raise RuntimeError("Failed to start Gradio server within timeout")
    
    def stop_server(self):
        """Stop the Gradio server."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None
        self.ready = False
    
    def is_ready(self):
        """Check if the server is ready."""
        return self.ready


@pytest.fixture(scope="session")
def gradio_server():
    """Session-scoped fixture to manage Gradio server."""
    server = GradioServerManager()
    
    try:
        server.start_server()
        yield server
    finally:
        server.stop_server()


@pytest.fixture
def page_with_server(page: Page, gradio_server):
    """Fixture that provides a page with the Gradio server running."""
    # Navigate to the Gradio app
    page.goto("http://127.0.0.1:7860")
    
    # Wait for the app to load
    page.wait_for_selector("h1", timeout=10000)
    
    return page


@pytest.mark.ui_automation
def test_gradio_app_loads(page_with_server: Page):
    """Test that the Gradio application loads successfully."""
    page = page_with_server
    
    # Check that the main title is present
    expect(page.locator("h1")).to_contain_text("Apiana AI Pipeline Runner")
    
    # Check that the pipeline dropdown is present
    dropdown = page.locator("#pipeline_selector")
    expect(dropdown).to_be_visible()
    
    # Take a screenshot for debugging
    page.screenshot(path="tests/ui_automation/screenshots/app_loaded.png")


@pytest.mark.ui_automation
def test_pipeline_dropdown_contains_dummy_pipeline(page_with_server: Page):
    """Test that the pipeline dropdown contains the dummy test pipeline."""
    page = page_with_server
    
    # Get the dropdown element
    dropdown = page.locator("#pipeline_selector")
    
    # Gradio dropdowns use a specific structure
    # First, check if the dropdown is visible
    expect(dropdown).to_be_visible()
    
    # Click on the dropdown input area
    dropdown_input = dropdown.locator("input").first
    dropdown_input.click()
    
    # Wait for dropdown options to appear
    page.wait_for_timeout(1000)
    
    # Take a screenshot to debug
    page.screenshot(path="tests/ui_automation/screenshots/dropdown_open.png")
    
    # Look for dummy_test_pipeline in the dropdown list
    # Gradio dropdowns create a separate div with options
    options = page.locator("[role='option']")
    
    # Check if any option contains dummy_test_pipeline
    found = False
    count = options.count()
    for i in range(count):
        text = options.nth(i).text_content()
        if "dummy_test_pipeline" in text:
            found = True
            break
    
    assert found, f"dummy_test_pipeline not found in dropdown. Found {count} options."


@pytest.mark.ui_automation
def test_select_dummy_pipeline_shows_parameters(page_with_server: Page):
    """Test that selecting the dummy pipeline shows its parameter form."""
    page = page_with_server
    
    # Select the dummy pipeline
    dropdown = page.locator("#pipeline_selector")
    dropdown_input = dropdown.locator("input").first
    dropdown_input.click()
    page.wait_for_timeout(500)
    
    # Find and click on dummy_test_pipeline option
    options = page.locator("[role='option']")
    for i in range(options.count()):
        if "dummy_test_pipeline" in options.nth(i).text_content():
            options.nth(i).click()
            break
    
    # Wait for the parameter form to render
    page.wait_for_timeout(1500)
    
    # Check that pipeline description is updated
    description = page.locator("#pipeline_description")
    expect(description).to_contain_text("Dummy Test Pipeline")
    expect(description).to_contain_text("Safe testing pipeline")
    
    # Check that parameter inputs are visible
    message_container = page.locator("#param_message")
    expect(message_container).to_be_visible()
    expect(message_container.locator("input, textarea").first).to_be_visible()
    
    iterations_container = page.locator("#param_iterations")
    expect(iterations_container).to_be_visible()
    expect(iterations_container.locator("input").first).to_be_visible()
    
    delay_container = page.locator("#param_delay_seconds")
    expect(delay_container).to_be_visible()
    expect(delay_container.locator("input").first).to_be_visible()
    
    # Check execute button is visible
    execute_btn = page.locator("#execute_button")
    expect(execute_btn).to_be_visible()
    
    # Take a screenshot
    page.screenshot(path="tests/ui_automation/screenshots/parameters_shown.png")


@pytest.mark.ui_automation
def test_fill_parameters_and_execute(page_with_server: Page):
    """Test filling in parameters and executing the pipeline."""
    page = page_with_server
    
    # Select the dummy pipeline
    assert select_gradio_dropdown(page, "pipeline_selector", "dummy_test_pipeline")
    page.wait_for_timeout(1500)
    
    # Fill in parameters - Gradio nests inputs within containers
    message_input = page.locator("#param_message").locator("input, textarea").first
    message_input.fill("Test message from UI automation")
    
    iterations_input = page.locator("#param_iterations").locator("input").first
    iterations_input.fill("2")  # Use 2 iterations for faster test
    
    delay_input = page.locator("#param_delay_seconds").locator("input").first
    delay_input.fill("0.5")
    
    # Take screenshot before execution
    page.screenshot(path="tests/ui_automation/screenshots/parameters_filled.png")
    
    # Click execute button
    execute_btn = page.locator("#execute_button")
    execute_btn.click()
    
    # Wait a moment for execution to start
    page.wait_for_timeout(2000)
    
    # Take screenshot after clicking execute
    page.screenshot(path="tests/ui_automation/screenshots/execution_started.png")


@pytest.mark.ui_automation
def test_execution_history_updates(page_with_server: Page):
    """Test that execution history shows updates during pipeline execution."""
    page = page_with_server
    
    # Select and execute the dummy pipeline
    assert select_gradio_dropdown(page, "pipeline_selector", "dummy_test_pipeline")
    page.wait_for_timeout(1500)
    
    # Fill minimal parameters - use longer delay to catch RUNNING state
    message_input = page.locator("#param_message").locator("input, textarea").first
    message_input.fill("Quick test")
    
    iterations_input = page.locator("#param_iterations").locator("input").first
    iterations_input.fill("3")
    
    delay_input = page.locator("#param_delay_seconds").locator("input").first
    delay_input.fill("1.0")
    
    # Execute
    execute_btn = page.locator("#execute_button")
    execute_btn.click()
    
    # Wait for execution to appear in history
    page.wait_for_timeout(1000)
    
    # Check for execution entry in the history markdown
    history_display = page.locator("#execution_history")
    expect(history_display).to_be_visible()
    
    # Check that the history contains the pipeline name and running status
    history_text = history_display.text_content()
    assert "dummy_test_pipeline" in history_text
    assert "RUNNING" in history_text
    
    # Check for the running emoji
    assert "🔄" in history_text
    
    # Take screenshot of running state
    page.screenshot(path="tests/ui_automation/screenshots/execution_running.png")


@pytest.mark.ui_automation
def test_execution_completes_successfully(page_with_server: Page):
    """Test that pipeline execution completes successfully with proper status updates."""
    page = page_with_server
    
    # Select and execute the dummy pipeline with short duration
    assert select_gradio_dropdown(page, "pipeline_selector", "dummy_test_pipeline")
    page.wait_for_timeout(1500)
    
    # Set very short execution time
    iterations_input = page.locator("#param_iterations").locator("input").first
    iterations_input.fill("1")
    
    delay_input = page.locator("#param_delay_seconds").locator("input").first
    delay_input.fill("0.1")
    
    # Execute
    execute_btn = page.locator("#execute_button")
    execute_btn.click()
    
    # Wait for completion (1 iteration * 0.1s delay + overhead)
    page.wait_for_timeout(3000)
    
    # Check for completed status in the history
    history_display = page.locator("#execution_history")
    history_text = history_display.text_content()
    assert "COMPLETED" in history_text
    
    # Check for success emoji
    success_emoji = page.locator("text=✅")
    expect(success_emoji).to_be_visible()
    
    # Verify execution time is shown
    duration_text = page.locator("text=/\\d+\\.\\d+s/")
    expect(duration_text).to_be_visible()
    
    # Take screenshot of completed state
    page.screenshot(path="tests/ui_automation/screenshots/execution_completed.png")


@pytest.mark.ui_automation
def test_logs_are_displayed_during_execution(page_with_server: Page):
    """Test that logs are displayed and updated during execution."""
    page = page_with_server
    
    # Select and execute the dummy pipeline
    assert select_gradio_dropdown(page, "pipeline_selector", "dummy_test_pipeline")
    page.wait_for_timeout(1500)
    
    # Set parameters for observable execution
    message_input = page.locator("#param_message").locator("input, textarea").first
    message_input.fill("Log test message")
    
    iterations_input = page.locator("#param_iterations").locator("input").first
    iterations_input.fill("3")
    
    delay_input = page.locator("#param_delay_seconds").locator("input").first
    delay_input.fill("0.5")
    
    # Execute
    execute_btn = page.locator("#execute_button")
    execute_btn.click()
    
    # Wait for execution to start
    page.wait_for_timeout(1000)
    
    # Get the execution history display
    history_display = page.locator("#execution_history")
    expect(history_display).to_be_visible()
    
    # Get initial history text
    initial_text = history_display.text_content()
    assert "RUNNING" in initial_text
    
    # Wait for logs to appear in the history
    page.wait_for_timeout(2000)
    
    # Check that logs are being displayed
    updated_text = history_display.text_content()
    
    # Verify log content appears
    assert "Recent Logs:" in updated_text
    assert len(updated_text) > len(initial_text)  # More content should have appeared
    
    # Take screenshot of logs
    page.screenshot(path="tests/ui_automation/screenshots/execution_logs.png")


@pytest.mark.ui_automation
def test_multiple_executions_in_history(page_with_server: Page):
    """Test that multiple executions appear in history with newest first."""
    page = page_with_server
    
    # Execute pipeline twice with different parameters
    for i in range(2):
        # Select pipeline
        assert select_gradio_dropdown(page, "pipeline_selector", "dummy_test_pipeline")
        page.wait_for_timeout(1500)
        
        # Set unique message
        message_input = page.locator("#param_message").locator("input, textarea").first
        message_input.fill(f"Execution {i+1}")
        
        iterations_input = page.locator("#param_iterations").locator("input").first
        iterations_input.fill("1")
        
        delay_input = page.locator("#param_delay_seconds").locator("input").first
        delay_input.fill("0.1")
        
        # Execute
        execute_btn = page.locator("#execute_button")
        execute_btn.click()
        
        # Wait before next execution
        page.wait_for_timeout(2000)
    
    # Verify both executions are in history
    history_display = page.locator("#execution_history")
    history_text = history_display.text_content()
    
    # Count occurrences of the pipeline name
    pipeline_count = history_text.count("dummy_test_pipeline")
    assert pipeline_count >= 2, f"Expected at least 2 executions, found {pipeline_count}"
    
    # Take screenshot
    page.screenshot(path="tests/ui_automation/screenshots/multiple_executions.png")


@pytest.mark.ui_automation
def test_clear_history_functionality(page_with_server: Page):
    """Test that clear history button removes all executions."""
    page = page_with_server
    
    # Execute a pipeline first
    assert select_gradio_dropdown(page, "pipeline_selector", "dummy_test_pipeline")
    page.wait_for_timeout(1500)
    
    execute_btn = page.locator("#execute_button")
    execute_btn.click()
    page.wait_for_timeout(2000)
    
    # Verify execution is in history
    history_display = page.locator("#execution_history")
    history_text = history_display.text_content()
    assert "dummy_test_pipeline" in history_text
    
    # Click clear history button
    clear_btn = page.locator("#clear_history")
    clear_btn.click()
    page.wait_for_timeout(1000)
    
    # Verify history is cleared
    cleared_text = history_display.text_content()
    assert "No executions yet" in cleared_text
    
    # Take screenshot
    page.screenshot(path="tests/ui_automation/screenshots/history_cleared.png")


@pytest.mark.ui_automation
def test_parameter_validation(page_with_server: Page):
    """Test that parameter inputs validate correctly."""
    page = page_with_server
    
    # Select the dummy pipeline
    assert select_gradio_dropdown(page, "pipeline_selector", "dummy_test_pipeline")
    page.wait_for_timeout(1500)
    
    # Test number input validation
    iterations_input = page.locator("#param_iterations").locator("input").first
    
    # Clear and enter non-numeric value (Gradio should prevent this)
    iterations_input.fill("")
    iterations_input.type("abc")
    
    # Verify the value is not accepted (should remain empty or show default)
    value = iterations_input.input_value()
    assert value == "" or value.isdigit()
    
    # Enter valid number
    iterations_input.fill("5")
    assert iterations_input.input_value() == "5"
    
    # Take screenshot
    page.screenshot(path="tests/ui_automation/screenshots/parameter_validation.png")


# Helper function to select from Gradio dropdown
def select_gradio_dropdown(page: Page, dropdown_id: str, option_text: str):
    """Helper to select an option from a Gradio dropdown."""
    dropdown = page.locator(f"#{dropdown_id}")
    dropdown_input = dropdown.locator("input").first
    dropdown_input.click()
    page.wait_for_timeout(500)
    
    # Find and click the option
    options = page.locator("[role='option']")
    for i in range(options.count()):
        if option_text in options.nth(i).text_content():
            options.nth(i).click()
            return True
    return False


# Helper function to run tests
def run_ui_tests():
    """Helper function to run UI tests programmatically."""
    import pytest
    return pytest.main([
        "tests/ui_automation/",
        "-v",
        "-m", "ui_automation",
        "--tb=short"
    ])


if __name__ == "__main__":
    # Run tests if script is executed directly
    run_ui_tests()