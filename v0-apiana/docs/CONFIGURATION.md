# Configuration Guide

Apiana AI uses a flexible configuration system based on dataclasses with support for Neo4j connection settings, LLM providers, and pipeline parameters.

## Core Configuration Classes

### Neo4jConfig

Manages connection to Neo4j database (Community Edition supported):

```python
from apiana.types.configuration import Neo4jConfig

config = Neo4jConfig(
    username="neo4j",
    password="password",
    host="localhost",
    port=7687,
    database=None  # Uses default 'neo4j' database
)
```

### Pipeline Configuration

Pipelines are configured through their factory functions in `pipelines.py`:

```python
from pipelines import chatgpt_full_processing_pipeline
from apiana.types.configuration import Neo4jConfig

pipeline = chatgpt_full_processing_pipeline(
    neo4j_config=config,
    agent_id="my_agent",
    input_file=Path("export.json"),
    llm_model="microsoft/DialoGPT-small",  # Local model
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    max_tokens=5000,
    min_messages=2
)
```

## Command-Line Interface

### ChatGPT Export CLI (v2)

The new modular CLI provides flexible configuration:

```bash
# Basic usage with defaults
uv run chatgpt-export-v2 -i export.json -o output/

# With custom Neo4j settings
uv run chatgpt-export-v2 -i export.json -o output/ \
    --neo4j-host localhost \
    --neo4j-port 7687 \
    --neo4j-password mypassword

# Using local LLM
uv run chatgpt-export-v2 -i export.json -o output/ \
    --local-llm microsoft/DialoGPT-small \
    --quantize-4bit

# Custom processing parameters
uv run chatgpt-export-v2 -i export.json -o output/ \
    --max-tokens 8000 \
    --min-messages 3 \
    --agent-id custom_agent
```

### Environment Variables

The system supports environment variables for sensitive configuration:

```bash
# Neo4j settings
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=password

# Run with environment config
uv run chatgpt-export-v2 -i export.json -o output/
```

## Gradio Web UI Configuration

The Gradio application automatically discovers pipelines and generates UI based on their parameters:

```python
# In pipelines.py, add metadata for UI generation
PIPELINE_REGISTRY = {
    "my_pipeline": PipelineMetadata(
        name="My Custom Pipeline",
        description="Description for UI",
        category="Processing",
        input_parameters={
            "param1": {"type": "string", "default": "value"},
            "param2": {"type": "integer", "default": 10}
        }
    )
}
```

## Storage Configuration

### ApplicationStore

For shared data storage:

```python
from apiana.stores import ApplicationStore
from apiana.types.configuration import Neo4jConfig

config = Neo4jConfig(username="neo4j", password="password")
store = ApplicationStore(config)
```

### AgentMemoryStore

For agent-specific memories (automatically tags with agent_id):

```python
from apiana.stores import AgentMemoryStore

# Each agent gets filtered memories in the shared database
agent_store = AgentMemoryStore(config, agent_id="agent_123")
```

## Provider Configuration

### Local LLM Providers

```python
from apiana.core.providers.local import LocalTransformersLLM

# Using Transformers models
llm = LocalTransformersLLM(
    model_name="microsoft/DialoGPT-small",
    device="auto",  # or "cpu", "cuda"
    quantize_4bit=True  # Optional quantization
)
```

### OpenAI-Compatible Providers

```python
from apiana.core.providers.openai import OpenAILLM

# Works with OpenAI, Ollama, or any compatible API
llm = OpenAILLM(
    model="gpt-4",
    api_key="your-key",
    base_url="https://api.openai.com/v1",  # or http://localhost:11434/v1 for Ollama
    temperature=0.7,
    max_tokens=4096
)
```

## Docker Configuration

The project includes docker-compose for Neo4j:

```yaml
# docker-compose.yml
services:
  neo4j:
    image: neo4j:5-community
    environment:
      - NEO4J_AUTH=neo4j/password
    ports:
      - "7474:7474"  # Web interface
      - "7687:7687"  # Bolt protocol
```

Start with: `docker-compose up -d`

## Testing Configuration

Run different test suites:

```bash
# Unit tests only (default)
make test

# Integration tests (requires Neo4j)
make test-integ

# UI automation tests (requires Playwright)
make test-ui

# All tests with environment checks
make test-comprehensive
```

## Best Practices

1. **Use environment variables** for sensitive data (passwords, API keys)
2. **Start with defaults** - Most parameters have sensible defaults
3. **Use local models** for privacy-sensitive data
4. **Configure agent_id** consistently across your application
5. **Monitor pipeline runs** using the PipelineRunManager

## Common Configurations

### Development Setup

```python
config = Neo4jConfig()  # Uses localhost defaults
pipeline = chatgpt_fragment_only_pipeline(
    neo4j_config=config,
    input_file=Path("test.json"),
    min_messages=1,  # Process all conversations
    tags=["dev", "test"]
)
```

### Production Setup

```python
config = Neo4jConfig(
    host=os.getenv("NEO4J_HOST"),
    password=os.getenv("NEO4J_PASSWORD")
)

pipeline = chatgpt_full_processing_pipeline(
    neo4j_config=config,
    agent_id=os.getenv("AGENT_ID"),
    input_file=Path(input_path),
    llm_model="gpt-4",  # Using OpenAI
    run_name=f"Production Run {datetime.now()}"
)
```