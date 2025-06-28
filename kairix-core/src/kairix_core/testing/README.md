# Kairix Core Testing Utilities

This module provides comprehensive mock implementations and fixtures for testing Kairix-based applications.

## Usage in External Packages

### 1. Basic Setup

In your project that depends on `kairix-core`, create a `conftest.py` file:

```python
# conftest.py in your project
from kairix_core.testing.conftest import *

# Add your own project-specific fixtures here
```

### 2. Using Individual Mocks

```python
import pytest
from kairix_core.types.cognition import Stimulus, StimulusType

def test_my_component(mock_agent_runtime):
    """Test using the mock agent runtime."""
    result = mock_agent_runtime.run("agent_name", "prompt")
    assert result.data == "Mock response"

@pytest.mark.asyncio
async def test_my_async_component(mock_conversational_persona):
    """Test using the mock persona."""
    stimulus = Stimulus(content="Hello", type=StimulusType.user_message)
    
    response = ""
    async for chunk in mock_conversational_persona.react(stimulus):
        response += chunk
    
    assert response == "Hello from mock persona!"
```

### 3. Creating Custom Mocks

```python
from kairix_core.testing.conftest import MockPerceptor, MockPersona
from kairix_core.types.cognition import Perception

# Custom perceptor with specific behavior
custom_perceptor = MockPerceptor(
    name="my_perceptor",
    perceptions=[
        Perception(source="my_source", content="Custom perception", confidence=0.9)
    ]
)

# Custom persona with specific responses
custom_persona = MockPersona(
    responses=["My", " custom", " response"]
)
```

### 4. Using the Complete Mock Environment

```python
def test_with_complete_environment(complete_mock_environment):
    """Test with all mocks configured."""
    env = complete_mock_environment
    
    # Access individual components
    agent_runtime = env['agent_runtime']
    neo4j_runtime = env['neo4j_runtime']
    cache_runtime = env['cache_runtime']
    
    # Everything is pre-configured and ready to use
    assert agent_runtime.configuration_set is not None
    assert neo4j_runtime.embedded_memory_shard_store is not None
```

## Available Fixtures

### Runtime Mocks
- `mock_agent_runtime`: Mock AgentRuntime singleton
- `mock_cache_runtime`: Mock CacheRuntime with dict-like behavior
- `mock_logging_runtime`: Mock LoggingRuntime with all log methods
- `mock_neo4j_runtime`: Mock Neo4j runtime with embedded stores

### Perceptor Mocks
- `mock_conversation_history_perceptor`: Returns conversation history
- `mock_environmental_context_perceptor`: Returns time/location/weather
- `mock_semantic_graph_perceptor`: Returns related concepts
- `mock_summary_insight_perceptor`: Returns historical insights

### Persona Mocks
- `mock_conversational_persona`: Streaming conversational responses

### Provider Mocks
- `mock_openai_provider`: Mock OpenAI inference provider
- `mock_llama_cpp_provider`: Mock llama.cpp provider

### Store Mocks
- `mock_embedded_data_store`: Mock vector store with search
- `mock_neo4j_models`: Mock Neo4j model classes

### Utility Mocks
- `mock_environment_variables`: Pre-configured environment variables
- `mock_httpx_client`: Mock HTTP client for API calls
- `mock_static_methods`: Common static methods (get_or_raise, etc.)
- `async_test_utils`: Utilities for async testing

### Complete Environment
- `complete_mock_environment`: All mocks configured together

## Mock Customization

All mocks can be customized for specific test needs:

```python
def test_custom_behavior(mock_agent_runtime):
    # Change return value
    mock_agent_runtime.run.return_value.data = "Custom response"
    
    # Add side effects
    mock_agent_runtime.run.side_effect = Exception("Test error")
    
    # Track calls
    mock_agent_runtime.run.assert_called_once_with("agent", "prompt")
```

## Async Testing Utilities

The `async_test_utils` fixture provides helpful async utilities:

```python
@pytest.mark.asyncio
async def test_async_timeout(async_test_utils):
    utils = async_test_utils
    
    # Collect async iterator results
    async def gen():
        yield 1
        yield 2
        yield 3
    
    results = await utils['collect_async_iter'](gen())
    assert results == [1, 2, 3]
    
    # Test with timeout
    async def slow_operation():
        await asyncio.sleep(10)
    
    with pytest.raises(asyncio.TimeoutError):
        await utils['timeout_after'](slow_operation(), seconds=0.1)
```

## Best Practices

1. **Import Strategy**: Import all fixtures with `from kairix_core.testing.conftest import *` in your conftest.py
2. **Mock Customization**: Customize mocks within individual tests rather than globally
3. **Async Tests**: Always use `@pytest.mark.asyncio` for async test functions
4. **Cleanup**: Mocks are automatically cleaned up after each test
5. **Type Hints**: Use type hints with mocks for better IDE support

## Example Project Structure

```
your-project/
├── src/
│   └── your_package/
│       └── ...
├── tests/
│   ├── conftest.py  # Import kairix mocks here
│   └── test_your_module.py
└── pyproject.toml
```

## Troubleshooting

### Import Errors
Make sure `kairix-core` is installed as a dependency:
```bash
uv add kairix-core
```

### Fixture Not Found
Ensure your conftest.py imports the testing module:
```python
from kairix_core.testing.conftest import *
```

### Async Test Failures
Don't forget the `@pytest.mark.asyncio` decorator on async tests.

### Mock Behavior Issues
Check that you're not accidentally sharing mock state between tests. Each test gets fresh mock instances.