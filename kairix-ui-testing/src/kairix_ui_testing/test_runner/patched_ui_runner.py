"""Run the real memory pipeline UI with patched dependencies."""

import click
import sys
from pathlib import Path
from unittest import mock

from ..mock_patches import create_mock_patches
from ..test_scenarios import TestScenarios


@click.command()
@click.option(
    "--scenario",
    type=click.Choice(["default", "streaming", "long-output", "error", "timeout", "empty", "mixed"]),
    default="default",
    help="Test scenario to use",
)
@click.option("--port", default=7860, help="Port to run the UI")
def run_patched_ui(scenario: str, port: int):
    """Run the real memory pipeline UI with mocked dependencies."""

    # Get test configuration
    scenario_map = {
        "default": TestScenarios.default,
        "streaming": TestScenarios.streaming_test,
        "long-output": TestScenarios.long_output_test,
        "error": TestScenarios.error_scenarios,
        "timeout": TestScenarios.timeout_scenario,
        "empty": TestScenarios.empty_state,
        "mixed": TestScenarios.mixed_success_failure,
    }
    config = scenario_map[scenario]()

    print(f"🎭 Running with scenario: {scenario}")
    print(f"📋 Configuration: {config}")

    # Create patches
    mock_functions = create_mock_patches(config)

    # Apply all patches
    with mock.patch.multiple(
        "kairix_offline.processing",
        **{
            "initialize_processing": mock_functions["kairix_offline.processing.initialize_processing"],
            "load_sources_from_gpt_export": mock_functions["kairix_offline.processing.load_sources_from_gpt_export"],
            "synth_memories": mock_functions["kairix_offline.processing.synth_memories"],
        },
    ):
        # Add kairix-offline to path
        offline_path = Path(__file__).parent.parent.parent.parent.parent / "kairix-offline" / "src"
        if str(offline_path) not in sys.path:
            sys.path.insert(0, str(offline_path))

        # Import and run the real UI
        from kairix_offline.ui.mem_ui import main

        print(f"🚀 Launching patched UI on port {port}")

        # Patch the launch to use our port
        original_launch = memory_pipeline.history_importer.launch

        def patched_launch(**kwargs):
            kwargs["server_port"] = port
            return original_launch(**kwargs)

        memory_pipeline.history_importer.launch = patched_launch

        try:
            main()
        except KeyboardInterrupt:
            print("\n👋 Shutting down")


if __name__ == "__main__":
    run_patched_ui()
