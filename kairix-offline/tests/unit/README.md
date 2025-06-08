# Unit Tests for kairix-offline

This directory contains unit tests that mock external dependencies.

## Running Unit Tests

```bash
cd kairix-offline
uv run pytest tests/unit/ -v
```

## Test Coverage

### test_summary_memory_synth.py
Tests for the SummaryMemorySynth class with mocked dependencies:
- Initialization
- Summary creation and reuse (idempotency)
- Embedding creation and reuse (idempotency)
- Chunk processing
- Memory shard creation and persistence
- Error handling

All external dependencies (chunker, embedder, generator, database) are mocked to ensure tests run without requiring:
- Neo4j database connection
- ML model downloads
- Environment variables