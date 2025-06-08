"""Test fixtures for patching the real UI."""

import pytest
from unittest import mock
from typing import Dict, Any
import sys
from pathlib import Path

from .mock_patches import create_mock_patches
from .test_scenarios import TestScenarios


@pytest.fixture
def patch_memory_pipeline(request):
    """Patch the memory pipeline with mock functions."""
    # Get config from test class or use default
    if hasattr(request, 'cls') and hasattr(request.cls, 'test_config'):
        config = request.cls.test_config
    else:
        config = TestScenarios.default()
    
    # Create mock patches instance that can be reconfigured
    mock_patches_instance = create_mock_patches(config)
    
    # Apply patches with the instance methods
    patches = []
    patch_map = {
        'kairix_offline.processing.initialize_processing': mock_patches_instance.mock_initialize_processing,
        'kairix_offline.processing.load_sources_from_gpt_export': mock_patches_instance.mock_load_sources_from_gpt_export,
        'kairix_offline.processing.synth_memories': mock_patches_instance.mock_synth_memories,
    }
    
    for module_path, mock_func in patch_map.items():
        patch = mock.patch(module_path, mock_func)
        patches.append(patch)
        patch.start()
    
    # Return the mock patches instance so tests can update config
    yield mock_patches_instance
    
    # Stop all patches
    for patch in patches:
        patch.stop()


@pytest.fixture(scope="session")
def ensure_kairix_offline_path():
    """Ensure kairix-offline is in the Python path."""
    offline_path = Path(__file__).parent.parent.parent / "kairix-offline" / "src"
    if str(offline_path) not in sys.path:
        sys.path.insert(0, str(offline_path))
    return str(offline_path)