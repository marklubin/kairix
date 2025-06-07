# Integration Tests

These integration tests require a running Neo4j database instance.

## Running the Integration Tests

1. **Start the Neo4j database:**
   ```bash
   docker-compose up -d neo4j
   ```

2. **Ensure your `.env` file has the correct Neo4j connection string:**
   ```
   NEO4J_URL=bolt://neo4j:password@localhost:7687
   ```

3. **Run the integration tests:**
   ```bash
   uv run pytest tests/integration/ -v
   ```

## What's Being Tested

### Mocked Components
- **LLM (Language Model)**: Returns predictable summaries
- **Embedder**: Returns consistent vector embeddings
- **Chunker**: Splits text into simple chunks

### Real Components
- **Neo4j Database**: All database operations are real
- **Neomodel ORM**: Real object-relational mapping
- **Graph Relationships**: Real node and relationship creation
- **Data Persistence**: Real data storage and retrieval

## Test Coverage

- `test_summary_memory_synth_integration.py`: Tests the complete memory synthesis pipeline with real database operations
- `test_gpt_loader_integration.py`: Tests loading ChatGPT conversations into the database

## Notes

- Tests will automatically clean the database before and after each test
- If `NEO4J_URL` is not set, integration tests will be skipped
- Make sure the Neo4j instance is accessible before running tests