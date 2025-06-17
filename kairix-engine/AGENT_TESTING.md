# Agent Testing and Model Verification

This project includes comprehensive testing for all agent configurations and model availability across different environments.

## Quick Start

### Verify All Models
```bash
# Quick verification of all models in all environments
just verify-models
```

### Run All Agent Tests
```bash
# Run comprehensive tests (included in `just all-tests`)
just test-all-agents
```

## Available Commands

### Model Verification
- `just verify-models` - Quick scan of all environments and available models
- `just test-model-discovery ENV` - Test model discovery for specific environment
- `just test-all-envs` - Check configuration for all environments

### Agent Testing
- `just test-agents ENV` - Test all agent configurations for one environment
- `just test-all-agents` - Comprehensive test of all environments with detailed output
- `just test-env-info ENV` - Quick environment check

### Integration Testing
- `just test-talk-smoke ENV` - Quick smoke tests for TTS/STT
- `just test-talk-integration ENV` - Full integration tests

## Output Examples

### Model Verification Output
```
🤖 MODEL VERIFICATION SUMMARY
============================================================

📁 Environment: cayucos
   Config: ollama-remote
   ✅ ollama-remote: 5 models
      q3r:latest, llama3.2:latest, phi3:latest
      ... and 2 more

📁 Environment: mac
   Config: openai
   ✅ openai: 5 models
      gpt-4o-mini, gpt-4o, gpt-3.5-turbo
      ... and 2 more

============================================================
✅ Working Environments: 2/2
📊 Total Models Available: 10
============================================================
```

### Comprehensive Test Output
```
🤖 KAIRIX ENGINE - COMPREHENSIVE AGENT TESTING
================================================================================
Started: 2024-06-17 10:30:00
================================================================================

────────────────────────────────────────────────
📋 Testing Environment: mac
────────────────────────────────────────────────

🔧 Environment: mac
   Config Set: openai
   User/Persona: test_user/assistant
   
   📦 Models Discovered: 5
      ✓ openai: gpt-4o-mini, gpt-4o, gpt-3.5-turbo
   
   🧪 Basic Chat Test: ✅ PASSED

================================================================================
📊 FINAL SUMMARY
================================================================================

Environments Tested: 2
Successful Environments: 2
Total Models Discovered: 10
Total Tests Run: 2
Total Tests Passed: 2

Overall Success Rate: 100.0%

📋 Environment Status:
   ✅ cayucos: 5 models
   ✅ mac: 5 models
```

## Test Results

Results are saved to `agent_test_results.json` with detailed information about:
- Environment configurations
- Discovered models per provider
- Test outcomes
- Error messages (if any)

## Environment Requirements

Each environment file (`env/{ENV}.env`) must include:
- `KAIRIX_AGENT_CONFIG_SET` - Agent configuration (openai, ollama-local, ollama-remote)
- `NEO4J_URL` - Database connection
- `KAIRIX_USER_NAME` - User identifier
- `KAIRIX_PERSONA_NAME` - AI persona name
- Provider-specific keys (OPENAI_API_KEY, etc.)

## Integration with CI/CD

The `just all-tests` target automatically runs agent verification as part of the full test suite. This ensures:
1. All configured models are accessible
2. Basic chat functionality works
3. Environment configurations are valid

## Troubleshooting

### No Models Found
- Check API keys are set correctly
- Verify network connectivity to providers
- Ensure Ollama is running (for local configurations)

### Test Failures
- Check Neo4j is accessible
- Verify all required environment variables are set
- Look at `agent_test_results.json` for detailed error messages

### Timeout Issues
- Tests timeout after 60 seconds
- May indicate network or provider issues
- Check provider status pages