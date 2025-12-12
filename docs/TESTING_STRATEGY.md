# Kairix E2E Testing Strategy

## Overview

This document outlines a comprehensive testing strategy for the Kairix conversational AI system, focusing on end-to-end verification testing while maintaining simplicity for a single-user application.

## Testing Philosophy

### Core Principles
1. **Test behavior, not implementation** - Focus on what the system does, not how
2. **Fast feedback loops** - Tests should run quickly to enable rapid iteration
3. **Deterministic results** - Tests must be reproducible and reliable
4. **Minimal mocking** - Prefer integration tests over heavily mocked unit tests
5. **Production parity** - Test environment should closely match production

## Testing Pyramid

```
         /\
        /E2E\         (10%) - Critical user journeys
       /------\
      /Contract\      (20%) - API compatibility
     /----------\
    /Integration \    (30%) - Component interactions
   /--------------\
  / Unit Testing   \  (40%) - Core logic and utilities
 /------------------\
```

## Test Suite Structure

```
tests/
├── e2e/                    # End-to-end tests
│   ├── test_conversation_flows.py
│   ├── test_memory_persistence.py
│   ├── test_streaming_api.py
│   └── test_context_awareness.py
├── contract/               # API contract tests
│   ├── test_openai_compatibility.py
│   └── test_api_schemas.py
├── integration/            # Integration tests
│   ├── test_persona_engine.py
│   ├── test_storage_layer.py
│   └── test_perceptor_system.py
├── unit/                   # Unit tests
│   ├── test_embeddings.py
│   ├── test_memory_utils.py
│   └── test_config.py
├── fixtures/               # Test data and fixtures
│   ├── conversations.json
│   ├── memory_snapshots.sql
│   └── mock_responses.json
├── conftest.py            # Shared pytest configuration
└── README.md              # Testing documentation
```

## E2E Test Scenarios

### 1. Conversation Flow Testing

```python
# tests/e2e/test_conversation_flows.py

import pytest
from httpx import AsyncClient
import asyncio
from typing import List, Dict

class TestConversationFlows:
    """Test complete conversation flows through the API."""

    @pytest.fixture
    async def client(self):
        """Create test client with running server."""
        from src.api.server import app
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_basic_conversation(self, client: AsyncClient):
        """Test a basic conversation with memory formation."""
        # Step 1: Send initial message
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "kairix-conversational",
                "messages": [
                    {"role": "user", "content": "My name is Alice and I love hiking"}
                ]
            },
            headers={"X-API-Key": "test-key"}
        )

        assert response.status_code == 200
        first_response = response.json()

        # Step 2: Send follow-up that requires memory
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "kairix-conversational",
                "messages": [
                    {"role": "user", "content": "My name is Alice and I love hiking"},
                    {"role": "assistant", "content": first_response["choices"][0]["message"]["content"]},
                    {"role": "user", "content": "What's my favorite activity?"}
                ]
            },
            headers={"X-API-Key": "test-key"}
        )

        assert response.status_code == 200
        second_response = response.json()

        # Verify memory recall
        assert "hiking" in second_response["choices"][0]["message"]["content"].lower()

    @pytest.mark.asyncio
    async def test_streaming_conversation(self, client: AsyncClient):
        """Test SSE streaming responses."""
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            json={
                "model": "kairix-conversational",
                "messages": [{"role": "user", "content": "Tell me a story"}],
                "stream": True
            },
            headers={"X-API-Key": "test-key"}
        ) as response:
            chunks = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk = line[6:]
                    if chunk != "[DONE]":
                        chunks.append(chunk)

            assert len(chunks) > 0
            # Verify chunks can be parsed
            import json
            for chunk in chunks:
                json.loads(chunk)

    @pytest.mark.asyncio
    async def test_context_awareness(self, client: AsyncClient):
        """Test environmental context updates affect responses."""
        # Update context
        await client.post(
            "/context/update",
            json={
                "session_id": "test-session",
                "timestamp": 1234567890,
                "geolocation": {
                    "latitude": 34.0522,
                    "longitude": -118.2437,
                    "city": "Los Angeles"
                },
                "activity": {
                    "activity_type": "walking",
                    "confidence": 0.9
                }
            },
            headers={"X-API-Key": "test-key"}
        )

        # Send message that should use context
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "kairix-conversational",
                "messages": [
                    {"role": "user", "content": "What's the weather like where I am?"}
                ]
            },
            headers={"X-API-Key": "test-key"}
        )

        assert response.status_code == 200
        content = response.json()["choices"][0]["message"]["content"].lower()
        # Should reference location
        assert any(word in content for word in ["los angeles", "la", "southern california"])
```

### 2. Memory Persistence Testing

```python
# tests/e2e/test_memory_persistence.py

class TestMemoryPersistence:
    """Test memory storage and retrieval across sessions."""

    @pytest.mark.asyncio
    async def test_memory_survives_restart(self, tmp_path):
        """Test that memories persist across server restarts."""
        db_path = tmp_path / "test.db"

        # Start server with test database
        server1 = await start_test_server(db_path=str(db_path))

        # Create memories
        await create_conversation(
            server1,
            [
                ("user", "I'm planning a trip to Japan"),
                ("assistant", "That sounds exciting!"),
                ("user", "I want to visit Tokyo and Kyoto")
            ]
        )

        # Stop server
        await server1.stop()

        # Start new server with same database
        server2 = await start_test_server(db_path=str(db_path))

        # Verify memories are recalled
        response = await query_server(
            server2,
            "What trip was I planning?"
        )

        assert "japan" in response.lower()
        assert any(city in response.lower() for city in ["tokyo", "kyoto"])

    @pytest.mark.asyncio
    async def test_incremental_summarization(self, client):
        """Test that conversations are incrementally summarized."""
        # Send multiple messages to trigger summarization
        for i in range(10):
            await client.post(
                "/v1/chat/completions",
                json={
                    "model": "kairix-conversational",
                    "messages": [
                        {"role": "user", "content": f"Message {i}: Tell me fact {i}"}
                    ]
                }
            )

        # Query for summary
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "kairix-conversational",
                "messages": [
                    {"role": "user", "content": "What have we discussed so far?"}
                ]
            }
        )

        content = response.json()["choices"][0]["message"]["content"]
        # Should reference multiple topics, not just recent ones
        assert "fact" in content.lower()
```

### 3. Performance Testing

```python
# tests/e2e/test_performance.py

class TestPerformance:
    """Test system performance characteristics."""

    @pytest.mark.asyncio
    async def test_response_latency(self, client):
        """Test that responses are generated within acceptable time."""
        import time

        start = time.time()
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "kairix-conversational",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 5.0  # Should respond within 5 seconds

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client):
        """Test handling multiple concurrent requests."""
        async def make_request(msg: str):
            return await client.post(
                "/v1/chat/completions",
                json={
                    "model": "kairix-conversational",
                    "messages": [{"role": "user", "content": msg}]
                }
            )

        # Send 5 concurrent requests
        tasks = [make_request(f"Request {i}") for i in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

    @pytest.mark.asyncio
    async def test_memory_limits(self, client):
        """Test system behavior at memory limits."""
        # Send many messages to fill conversation history
        for i in range(100):
            await client.post(
                "/v1/chat/completions",
                json={
                    "model": "kairix-conversational",
                    "messages": [{"role": "user", "content": f"Message {i}"}]
                }
            )

        # System should still respond normally
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "kairix-conversational",
                "messages": [{"role": "user", "content": "Are you still working?"}]
            }
        )

        assert response.status_code == 200
```

## Contract Testing

```python
# tests/contract/test_openai_compatibility.py

from openai import OpenAI
import pytest

class TestOpenAICompatibility:
    """Test OpenAI API compatibility."""

    @pytest.fixture
    def openai_client(self, test_server):
        """Create OpenAI client pointed at test server."""
        return OpenAI(
            api_key="test-key",
            base_url=f"http://localhost:{test_server.port}/v1"
        )

    def test_chat_completion_format(self, openai_client):
        """Test that response matches OpenAI format."""
        response = openai_client.chat.completions.create(
            model="kairix-conversational",
            messages=[{"role": "user", "content": "Hello"}]
        )

        # Verify response structure
        assert hasattr(response, 'id')
        assert hasattr(response, 'model')
        assert hasattr(response, 'choices')
        assert len(response.choices) > 0
        assert hasattr(response.choices[0], 'message')
        assert hasattr(response.choices[0].message, 'content')

    def test_streaming_format(self, openai_client):
        """Test streaming response format."""
        stream = openai_client.chat.completions.create(
            model="kairix-conversational",
            messages=[{"role": "user", "content": "Hello"}],
            stream=True
        )

        chunks = list(stream)
        assert len(chunks) > 0

        # Verify chunk structure
        for chunk in chunks:
            assert hasattr(chunk, 'choices')
            if chunk.choices:
                assert hasattr(chunk.choices[0], 'delta')
```

## Test Data Management

### Fixtures and Factories

```python
# tests/fixtures/factories.py

from dataclasses import dataclass
from typing import List
import json

@dataclass
class ConversationFixture:
    """Reusable conversation for testing."""
    messages: List[dict]
    expected_memories: List[str]

    @classmethod
    def from_json(cls, path: str):
        """Load fixture from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls(**data)

class TestDataBuilder:
    """Builder for complex test scenarios."""

    @staticmethod
    def create_long_conversation(num_turns: int = 50):
        """Create a long conversation for testing."""
        messages = []
        for i in range(num_turns):
            messages.append({"role": "user", "content": f"User message {i}"})
            messages.append({"role": "assistant", "content": f"Response {i}"})
        return messages

    @staticmethod
    def create_context_scenario(location: str, activity: str):
        """Create environmental context scenario."""
        return {
            "geolocation": {"city": location},
            "activity": {"activity_type": activity}
        }
```

## Test Execution Strategy

### Local Development

```bash
# Run all tests
pytest tests/

# Run only E2E tests
pytest tests/e2e/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run in watch mode for development
pytest-watch tests/unit/

# Run with verbose output
pytest tests/ -v -s

# Run specific test
pytest tests/e2e/test_conversation_flows.py::TestConversationFlows::test_basic_conversation
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Install uv
      run: curl -LsSf https://astral.sh/uv/install.sh | sh

    - name: Install dependencies
      run: uv sync

    - name: Run unit tests
      run: uv run pytest tests/unit/ -v

    - name: Run integration tests
      run: uv run pytest tests/integration/ -v

    - name: Run contract tests
      run: uv run pytest tests/contract/ -v

    - name: Run E2E tests
      run: uv run pytest tests/e2e/ -v

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Performance Benchmarking

```python
# tests/benchmarks/bench_api.py

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

def test_response_generation_benchmark(benchmark: BenchmarkFixture, client):
    """Benchmark response generation."""
    def generate_response():
        return client.post(
            "/v1/chat/completions",
            json={
                "model": "kairix-conversational",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )

    result = benchmark(generate_response)
    assert result.status_code == 200

def test_memory_search_benchmark(benchmark: BenchmarkFixture, storage):
    """Benchmark vector similarity search."""
    embedding = [0.1] * 768  # Mock embedding

    def search_memories():
        return storage.search_similar(embedding, k=5)

    results = benchmark(search_memories)
    assert len(results) <= 5
```

## Test Environment Configuration

### Environment Variables

```bash
# .env.test
KAIRIX_ENV=test
KAIRIX_LOG_LEVEL=DEBUG
KAIRIX_DB_PATH=:memory:  # Use in-memory SQLite for tests
KAIRIX_API_KEY=test-key
KAIRIX_MODEL_PROVIDER=mock
KAIRIX_MOCK_RESPONSES=true
```

### Docker Test Environment

```dockerfile
# Dockerfile.test
FROM python:3.11-slim

WORKDIR /app

# Install test dependencies
RUN pip install uv
COPY pyproject.toml .
RUN uv sync

# Copy source and tests
COPY src/ src/
COPY tests/ tests/

# Run tests
CMD ["uv", "run", "pytest", "tests/", "-v"]
```

## Monitoring & Debugging

### Test Observability

```python
# tests/conftest.py

import logging
import pytest
from pathlib import Path

@pytest.fixture(autouse=True)
def configure_test_logging(caplog):
    """Configure logging for tests."""
    caplog.set_level(logging.DEBUG)

@pytest.fixture
def save_test_artifacts(request, tmp_path):
    """Save test artifacts for debugging."""
    def save_artifact(name: str, content: str):
        artifact_dir = Path("test-artifacts") / request.node.name
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / name).write_text(content)

    return save_artifact

# Usage in tests
def test_complex_scenario(save_test_artifacts):
    response = make_api_call()
    save_test_artifacts("response.json", response.text)
```

### Test Debugging Tools

```python
# tests/utils/debug.py

class TestDebugger:
    """Utilities for debugging test failures."""

    @staticmethod
    def dump_database(db_path: str):
        """Dump database state for inspection."""
        import sqlite3
        conn = sqlite3.connect(db_path)
        with open("db_dump.sql", "w") as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")

    @staticmethod
    def capture_api_traffic(client):
        """Capture all API traffic for analysis."""
        import httpx

        class LoggingTransport(httpx.HTTPTransport):
            def handle_request(self, request):
                print(f"REQUEST: {request.method} {request.url}")
                print(f"BODY: {request.content}")
                response = super().handle_request(request)
                print(f"RESPONSE: {response.status_code}")
                return response

        client._transport = LoggingTransport()
        return client
```

## Success Metrics

### Coverage Goals
- Overall: 90% code coverage
- Core logic: 95% coverage
- API endpoints: 100% coverage
- Error paths: 85% coverage

### Performance Targets
- Unit tests: < 1 second each
- Integration tests: < 5 seconds each
- E2E tests: < 30 seconds each
- Full suite: < 5 minutes

### Reliability Metrics
- Zero flaky tests
- 100% deterministic results
- All tests pass on first run

## Continuous Improvement

### Test Review Checklist
- [ ] Does the test have a clear purpose?
- [ ] Is the test independent of other tests?
- [ ] Does the test use meaningful assertions?
- [ ] Is the test data realistic?
- [ ] Does the test cover edge cases?
- [ ] Is the test maintainable?

### Monthly Test Audit
1. Review test execution times
2. Identify and fix flaky tests
3. Update test data to match production
4. Review coverage gaps
5. Refactor complex tests
6. Update documentation

## Conclusion

This testing strategy provides comprehensive coverage while maintaining simplicity and speed. The focus on E2E testing ensures the system works correctly from the user's perspective, while the supporting test layers provide fast feedback during development. The emphasis on deterministic, independent tests ensures reliability and maintainability as the system evolves.