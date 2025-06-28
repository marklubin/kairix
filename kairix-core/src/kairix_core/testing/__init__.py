"""Testing utilities and fixtures for kairix-core.

This module provides shared testing infrastructure that can be used by both
internal tests and external packages that depend on kairix-core.

Example usage in external packages:
    # In your project's conftest.py
    from kairix_core.testing.conftest import *
    
    # Or import specific fixtures
    from kairix_core.testing.conftest import (
        mock_agent_runtime,
        mock_conversational_persona,
        complete_mock_environment
    )
"""

# Re-export all fixtures and utilities for convenience
from .conftest import (
    # Mock data classes
    MockAgent,
    MockRunResult,
    MockRunResultStreaming,
    # Mock implementations
    MockPerceptor,
    MockPersona,
    MockInferenceProvider,
    # Fixtures - these are for documentation, actual fixtures are imported via *
    mock_conversation_history_perceptor,
    mock_environmental_context_perceptor,
    mock_semantic_graph_perceptor,
    mock_summary_insight_perceptor,
    mock_conversational_persona,
    mock_agent_runtime,
    mock_cache_runtime,
    mock_logging_runtime,
    mock_neo4j_runtime,
    mock_openai_provider,
    mock_llama_cpp_provider,
    mock_embedded_data_store,
    mock_neo4j_connection,
    mock_neo4j_models,
    mock_environment_variables,
    mock_httpx_client,
    mock_static_methods,
    complete_mock_environment,
    async_test_utils,
)

__all__ = [
    # Mock data classes
    'MockAgent',
    'MockRunResult', 
    'MockRunResultStreaming',
    
    # Mock implementations
    'MockPerceptor',
    'MockPersona',
    'MockInferenceProvider',
    
    # Fixture names (for documentation)
    'mock_conversation_history_perceptor',
    'mock_environmental_context_perceptor',
    'mock_semantic_graph_perceptor',
    'mock_summary_insight_perceptor',
    'mock_conversational_persona',
    'mock_agent_runtime',
    'mock_cache_runtime',
    'mock_logging_runtime',
    'mock_neo4j_runtime',
    'mock_openai_provider',
    'mock_llama_cpp_provider',
    'mock_embedded_data_store',
    'mock_neo4j_connection',
    'mock_neo4j_models',
    'mock_environment_variables',
    'mock_httpx_client',
    'mock_static_methods',
    'complete_mock_environment',
    'async_test_utils',
]