# Agent Configuration Tests

This directory contains integration tests that verify all possible agent configurations work with real API endpoints.

## Test Structure

### `test_agent_configurations.py`
Tests model discovery and all permutations of agent configurations:
- Discovers available models from each provider (OpenAI, Ollama local/remote)
- Generates all possible combinations of models for different agent roles
- Tests each configuration with real API calls
- Verifies non-empty responses

### `test_chat_configurations.py`
Tests the full Chat functionality with different environments:
- Basic chat interactions
- Conversation continuity and context
- Model-specific capabilities
- Error handling and edge cases
- Concurrent chat sessions

## Running Tests

### Quick Environment Check
```bash
# Check mac environment
just test-env-info mac

# Check cayucos environment
just test-env-info cayucos
```

### Test Model Discovery
```bash
# Discover available models
just test-model-discovery mac
```

### Run Full Agent Tests
```bash
# Test all agent configurations
just test-agents mac

# Or use the script directly
python run_agent_tests.py --env mac --test full
```

### Test Specific Functionality
```bash
# Basic chat test
ENV=mac uv run pytest tests/integration/test_chat_configurations.py::TestChatConfigurations::test_basic_chat_interaction -v -s

# Concurrent sessions
ENV=mac uv run pytest tests/integration/test_chat_configurations.py::TestChatConfigurations::test_concurrent_chats -v -s
```

## Environment Requirements

Each environment needs these variables set in `env/{ENV}.env`:

### Required for all tests:
- `KAIRIX_AGENT_CONFIG_SET` - Which agent configuration to use (openai, ollama-local, ollama-remote)
- `NEO4J_URL` - Neo4j database connection
- `KAIRIX_N_SUMMARIES_PER_MESSAGE` - Number of summaries per message
- `KAIRIX_USER_NAME` - User name for chat
- `KAIRIX_PERSONA_NAME` - AI persona name

### Provider-specific:
- `OPENAI_API_KEY` - Required if using openai configuration
- Ollama endpoints must be accessible:
  - Local: http://localhost:11434
  - Remote: https://ollama.kairix.net

## Test Results

Tests are considered passing if:
1. Model discovery finds at least one model
2. Agent responds with non-empty text
3. Basic conversation flow works
4. At least 80% of test prompts succeed

## Debugging

Use `test-env-info` to check:
- Which environment variables are set
- Endpoint connectivity
- Available models

Example output:
```
==================================================
Environment Configuration Summary
==================================================
Environment: mac
Agent Config Set: openai
User Name: test_user
Persona Name: assistant
Neo4j URL: ✓
OpenAI API Key: ✓
Summaries per Message: 5

Endpoint Connectivity:
  Neo4j: ✓
  OpenAI: ✓ (128 models)
==================================================
```

## Adding New Tests

To test a new model or provider:
1. Add provider mapping in `kairix_engine/engine.py`
2. Add discovery method in `test_agent_configurations.py`
3. Create environment file with required variables
4. Run discovery test first to verify connectivity