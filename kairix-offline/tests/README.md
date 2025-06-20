# Knowledge DB Demo Test Suite

This directory contains comprehensive tests for the `knowledge_db_demo.py` script.

## Test Structure

- **`test_knowledge_db_demo.py`** - Main unit tests covering:
  - Data models (Unit, Relation, Extraction)
  - Extraction agents functionality
  - Vector search operations
  - Semantic unit deduplication logic
  - Basic integration tests
  - Error handling

- **`test_knowledge_db_demo_edge_cases.py`** - Edge cases and boundary conditions:
  - Empty/None data handling
  - Special characters and encoding
  - Database interaction edge cases
  - Performance and memory considerations
  - Concurrent operations

- **`test_knowledge_db_demo_integration.py`** - Full integration tests:
  - End-to-end workflow testing
  - Agent specialization verification
  - Multi-summary deduplication
  - Error recovery scenarios
  - Performance benchmarks

- **`conftest.py`** - Shared test configuration:
  - Automatic Neo4j mocking
  - Sentence transformer mocking
  - Common fixtures
  - PYTEST_RUN environment setup

## Running Tests

```bash
# Run all tests
pytest tests/

# Run only unit tests
pytest tests/test_knowledge_db_demo.py -v

# Run only integration tests
pytest tests/ -m integration -v

# Run with coverage
pytest tests/ --cov=scripts.knowledge_db_demo --cov-report=html

# Run excluding slow tests
pytest tests/ -m "not slow"
```

## Test Categories

Tests are marked with the following categories:
- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (moderate speed)
- `@pytest.mark.slow` - Performance/stress tests (slow)

## Key Testing Patterns

1. **Neo4j Mocking**: All database operations are automatically mocked via `conftest.py`
2. **Async Testing**: Uses `pytest.mark.asyncio` for async function testing
3. **Agent Mocking**: Runner.run is mocked to simulate agent responses
4. **Environment Isolation**: PYTEST_RUN environment variable prevents real DB connections

## Test Coverage

The test suite covers:
- ✅ All public functions and methods
- ✅ Error handling and edge cases
- ✅ Concurrent execution verification
- ✅ Data validation and type safety
- ✅ Integration between components
- ✅ Performance characteristics

## Adding New Tests

When adding new tests:
1. Use appropriate fixtures from `conftest.py`
2. Mark tests with appropriate categories
3. Mock external dependencies (Neo4j, embedder, agents)
4. Test both success and failure scenarios
5. Verify concurrent behavior where applicable