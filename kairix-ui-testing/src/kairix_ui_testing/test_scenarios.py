"""Pre-configured test scenarios for UI testing."""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class UITestScenario:
    """Configuration for a specific UI test scenario."""
    name: str
    description: str
    mock_config: Dict[str, Any]
    expected_behaviors: Dict[str, str]


class TestScenarios:
    """Collection of pre-configured test scenarios."""
    
    @staticmethod
    def default() -> Dict[str, Any]:
        """Default configuration for normal operation."""
        return {
            "mock_conversation_count": 5,
            "summarize_delay": 1.0,
            "default_file_exists": True,
        }
    
    @staticmethod
    def streaming_test() -> Dict[str, Any]:
        """Configuration for testing streaming output."""
        return {
            "mock_conversation_count": 10,
            "summarize_delay": 0.5,
            "import_delay_per_conversation": 0.1,
        }
    
    @staticmethod
    def long_output_test() -> Dict[str, Any]:
        """Configuration for testing scrolling with long output."""
        return {
            "mock_conversation_count": 100,
            "summarize_delay": 0.1,
            "mock_memory_shard_count": 500,
        }
    
    @staticmethod
    def error_scenarios() -> Dict[str, Any]:
        """Configuration for testing error states."""
        return {
            "import_should_fail": True,
            "import_failure_message": "❌ Database connection failed",
            "summarize_should_fail": False,
        }
    
    @staticmethod
    def timeout_scenario() -> Dict[str, Any]:
        """Configuration for testing timeout behavior."""
        return {
            "mock_conversation_count": 5,
            "summarize_should_timeout": True,
            "summarize_delay": 3.0,
        }
    
    @staticmethod
    def empty_state() -> Dict[str, Any]:
        """Configuration for testing with no default file."""
        return {
            "default_file_exists": False,
            "mock_conversation_count": 0,
        }
    
    @staticmethod
    def mixed_success_failure() -> Dict[str, Any]:
        """Configuration with some conversations failing."""
        return {
            "mock_conversation_count": 20,
            "random_failures": True,
            "summarize_delay": 1.0,
        }
    
    @staticmethod
    def no_file_selected() -> Dict[str, Any]:
        """Scenario where no file is selected."""
        return {
            "no_file_selected": True,
        }
    
    @staticmethod
    def import_failure() -> Dict[str, Any]:
        """Scenario where import fails."""
        return {
            "import_should_fail": True,
            "import_failure_message": "Import failed: Mock processing error",
        }
    
    @staticmethod
    def synthesis_validation() -> Dict[str, Any]:
        """Scenario for synthesis validation."""
        return {
            "synthesis_validate_inputs": True,
        }
    
    @staticmethod
    def synthesis_no_data() -> Dict[str, Any]:
        """Scenario where no data has been imported."""
        return {
            "synthesis_no_data": True,
        }


# UI Test Scenarios with expected behaviors
UI_TEST_SCENARIOS = [
    UITestScenario(
        name="happy_path",
        description="Everything works perfectly",
        mock_config=TestScenarios.default(),
        expected_behaviors={
            "import_streaming": "Text appears line by line",
            "import_final": "Shows 'finished! Wrote Source Documents'",
            "synthesis_output": "Shows memory shard counts",
        }
    ),
    UITestScenario(
        name="import_error",
        description="Import fails with error message",
        mock_config=TestScenarios.error_scenarios(),
        expected_behaviors={
            "import_starts": "Shows 'Loading' message",
            "import_fails": "Shows error message",
            "synthesis_blocked": "Cannot synthesize without import",
        }
    ),
    UITestScenario(
        name="long_scrolling",
        description="Many items for scroll testing",
        mock_config=TestScenarios.long_output_test(),
        expected_behaviors={
            "scrollbar_appears": "Vertical scrollbar visible",
            "auto_scroll": "Scrolls to bottom during streaming",
            "manual_scroll": "Can scroll up while streaming",
        }
    ),
]