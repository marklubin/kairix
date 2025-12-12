# Kairix Environment Variables Documentation

This document provides comprehensive documentation for all environment variables used in the Kairix project, including their purpose, current usage status, and default values.

## Table of Contents
1. [Core Configuration](#core-configuration)
2. [Inference & AI Models](#inference--ai-models)
3. [Summarization](#summarization)
4. [Embeddings](#embeddings)
5. [Processing & Memory](#processing--memory)
6. [External Services](#external-services)
7. [Database](#database)
8. [Frontend (Vite)](#frontend-vite)
9. [Testing & Development](#testing--development)
10. [Platform-Specific](#platform-specific)

## Core Configuration

### KAIRIX_APP_ID
- **Purpose**: Identifies the application instance (e.g., "server", "client")
- **Status**: ✅ Active
- **Default**: `"server"`
- **Used in**: `kairix-apps/src/kairix_apps/server.py:4`
- **Notes**: Set programmatically via `os.putenv()` in server.py

### KAIRIX_SERVER_PORT
- **Purpose**: Port number for the Kairix API server
- **Status**: ✅ Active
- **Default**: `8888`
- **Used in**: `kairix-apps/src/kairix_apps/server.py:37`
- **Notes**: Critical for API server configuration

### KAIRIX_LOG_LEVEL
- **Purpose**: Controls logging verbosity (DEBUG, INFO, WARNING, ERROR)
- **Status**: ✅ Active
- **Default**: `"INFO"`
- **Used in**: `kairix-apps/src/kairix_apps/server.py:38-39`
- **Notes**: Optional, defaults to INFO if not set

### KAIRIX_API_KEY
- **Purpose**: API key for authenticating requests to Kairix server
- **Status**: ⚠️ Partially Active
- **Default**: Not set
- **Used in**: `kairix-apps/src/kairix_apps/server.py:44`
- **Notes**: Optional authentication mechanism

### KAIRIX_USER_NAME
- **Purpose**: Display name for the human user in conversations
- **Status**: ✅ Active
- **Default**: `"Mark"`
- **Used in**: 
  - `kairix-apps/src/kairix_apps/engine.py:43`
  - `kairix-core/src/kairix_core/runtime/logging.py:41`
- **Notes**: Personalizes the conversation experience

### KAIRIX_PERSONA_NAME
- **Purpose**: Display name for the AI assistant persona
- **Status**: ✅ Active
- **Default**: `"Kairix"`
- **Used in**: `kairix-apps/src/kairix_apps/engine.py:44`
- **Notes**: Used in conversations and UI display

### KAIRIX_AGENT_CONFIGURATION_SET_KEY
- **Purpose**: Key to identify which agent configuration set to use
- **Status**: ✅ Active
- **Default**: `"base"`
- **Used in**: 
  - `kairix-apps/src/kairix_apps/engine.py:40`
  - `kairix-core/src/kairix_core/runtime/agent.py:33`
- **Notes**: Allows switching between different agent configurations

### KAIRIX_MCP_SERVER
- **Purpose**: Model Context Protocol server configuration
- **Status**: ❌ Inactive (Commented out)
- **Default**: Not set
- **Used in**: `kairix-core/src/kairix_core/runtime/agent.py:37`
- **Notes**: For future MCP integration

## Inference & AI Models

### KAIRIX_DEFAULT_INFERENCE_MODEL
- **Purpose**: Default LLM model for inference
- **Status**: ✅ Active
- **Default**: `"gpt-4o"`
- **Used in**: `kairix-core/src/kairix_core/configuration/agent.py:18`
- **Notes**: Can be overridden by specific provider settings

### KAIRIX_INFERENCE_PROVIDER
- **Purpose**: Specifies which inference provider to use
- **Status**: ✅ Active
- **Default**: `"openai"`
- **Options**: `"openai"`, `"ollama"`, `"llama_cpp"`
- **Used in**: `kairix-core/src/kairix_core/inference/inference_provider.py:75`

### KAIRIX_INFERENCE_API_KEY
- **Purpose**: API key for inference provider (e.g., OpenAI)
- **Status**: ✅ Active
- **Default**: `"MISSING_API_KEY"` (requires user to set)
- **Used in**: `kairix-core/src/kairix_core/inference/inference_provider.py:80`
- **Notes**: Required for OpenAI, optional for local providers

### KAIRIX_INFERENCE_BASE_URL
- **Purpose**: Base URL for inference API endpoint
- **Status**: ✅ Active
- **Default**: Varies by provider:
  - OpenAI: `"https://api.openai.com/v1"`
  - Ollama: `"http://host.docker.internal:11434/v1"`
- **Used in**: `kairix-core/src/kairix_core/inference/inference_provider.py:90`

### KAIRIX_INFERENCE_EMBEDDING_DIMS
- **Purpose**: Dimension size for inference embeddings
- **Status**: ✅ Active
- **Default**: `1536` (OpenAI), `768` (Ollama)
- **Used in**: Configuration files
- **Notes**: Must match the embedding model's output dimensions

### TOKENIZERS_PARALLELISM
- **Purpose**: Controls HuggingFace tokenizer parallelism
- **Status**: ✅ Active
- **Default**: `"false"`
- **Used in**: All environment files
- **Notes**: Set to false to avoid warnings in multi-threaded environments

## Summarization

### KAIRIX_SUMMARIZER_MODEL
- **Purpose**: Model used for text summarization
- **Status**: ✅ Active
- **Default**: `"facebook/bart-large-cnn"`
- **Used in**: `kairix-offline/src/kairix_offline/processing/__init__.py:33`

### KAIRIX_SUMMARIZER_ENABLE_QUANTIZATION
- **Purpose**: Enable 4-bit quantization for summarizer model
- **Status**: ✅ Active
- **Default**: `"False"`
- **Used in**: `kairix-offline/src/kairix_offline/processing/__init__.py:34`
- **Notes**: Reduces memory usage but may impact quality

### KAIRIX_SUMMARIZER_MAX_TOKENS
- **Purpose**: Maximum tokens for summarization output
- **Status**: ✅ Active
- **Default**: `142`
- **Used in**: `kairix-offline/src/kairix_offline/processing/__init__.py:45`

### KAIRIX_SUMMARIZER_TEMPERATURE
- **Purpose**: Temperature for summarization generation
- **Status**: ✅ Active
- **Default**: `1.0`
- **Used in**: `kairix-offline/src/kairix_offline/processing/__init__.py:46`

### KAIRIX_SUMMARIZATION_INTERVAL
- **Purpose**: How often to trigger summarization (in messages)
- **Status**: ✅ Active
- **Default**: `10`
- **Used in**: `kairix-apps/src/kairix_apps/engine.py:45`

### KAIRIX_N_SUMMARIES_PER_MESSAGE
- **Purpose**: Number of summaries to generate per message
- **Status**: ✅ Active
- **Default**: `3`
- **Used in**: `kairix-apps/src/kairix_apps/engine.py:41`

## Embeddings

### KAIRIX_EMBEDDER_MODEL
- **Purpose**: Model for generating text embeddings
- **Status**: ✅ Active
- **Default**: `"sentence-transformers/all-MiniLM-L6-v2"`
- **Used in**: 
  - `kairix-apps/src/kairix_apps/engine.py:60`
  - `kairix-offline/src/kairix_offline/processing/__init__.py:93`

### KAIRIX_EMBEDDER_DEVICE
- **Purpose**: Device for embedding computation
- **Status**: ✅ Active
- **Default**: Platform-specific:
  - CPU: `"cpu"`
  - CUDA: `"cuda"`
  - MPS (Mac): `"mps"`
- **Used in**: 
  - `kairix-apps/src/kairix_apps/engine.py:61`
  - `kairix-offline/src/kairix_offline/processing/__init__.py:94`

### KAIRIX_EMBEDDING_BATCH_SIZE
- **Purpose**: Batch size for embedding generation
- **Status**: ✅ Active
- **Default**: `32`
- **Used in**: `kairix-offline/src/kairix_offline/processing/__init__.py:95`

### KAIRIX_SEMANTIC_EMBEDDING_MODEL
- **Purpose**: Model for semantic embeddings
- **Status**: ✅ Active
- **Default**: `"all-MiniLM-L6-v2"`
- **Used in**: Test configurations
- **Notes**: Different from regular embedder for semantic search

### KAIRIX_SEMANTIC_EMBEDDING_DIMS
- **Purpose**: Dimensions for semantic embeddings
- **Status**: ✅ Active
- **Default**: `384`
- **Used in**: Test configurations

## Processing & Memory

### KAIRIX_CHUNK_SIZE
- **Purpose**: Size of text chunks for processing
- **Status**: ✅ Active
- **Default**: `1000`
- **Used in**: `kairix-offline/src/kairix_offline/processing/__init__.py:89`

### KAIRIX_MESSAGE_RETENTION_WINDOW
- **Purpose**: Number of recent messages to keep in active memory
- **Status**: ✅ Active
- **Default**: `200`
- **Used in**: `kairix-apps/src/kairix_apps/engine.py:46`

### KAIRIX_SUMMARY_EXTRACTION_PARALLELISM
- **Purpose**: Parallel workers for summary extraction
- **Status**: ✅ Active
- **Default**: `4`
- **Used in**: 
  - `kairix-offline/src/kairix_offline/jobs/extract_facts_from_summaries.py:39`
  - Test configurations

## External Services

### OPENAI_API_KEY
- **Purpose**: OpenAI API authentication
- **Status**: ✅ Active
- **Default**: User must provide
- **Used in**: 
  - `kairix-offline/src/kairix_offline/eval/inference_eval.py:97`
  - `kairix-sre-agent/sre_agent/config.py:54`
- **Notes**: ⚠️ Currently exposed in some config files - should be secured

### ELEVENLABS_API_KEY
- **Purpose**: ElevenLabs text-to-speech API key
- **Status**: ✅ Active (in tests)
- **Default**: User must provide
- **Used in**: Multiple test files
- **Notes**: ⚠️ Currently exposed in config files - should be secured

### ELEVENLABS_VOICE_ID
- **Purpose**: Voice selection for TTS
- **Status**: ✅ Active
- **Default**: `"EXAVITQu4vr4xnSDxMaL"`

### ELEVENLABS_MODEL_ID
- **Purpose**: TTS model selection
- **Status**: ✅ Active
- **Default**: `"eleven_multilingual_v2"`

### BRAVE_API_KEY
- **Purpose**: Brave Search API authentication
- **Status**: ✅ Active
- **Default**: Set in config files
- **Notes**: ⚠️ Currently exposed - should be secured

## Database

### NEO4J_URL
- **Purpose**: Neo4j graph database connection URL
- **Status**: ⚠️ Transitioning (moving to SQLite)
- **Default**: `"bolt://localhost:7687"`
- **Used in**: `kairix-offline/scripts/backfill_summary_dates.py:15`
- **Notes**: Being phased out in favor of SQLite

### KAIRIX_DATABASE_URL
- **Purpose**: Primary database connection URL
- **Status**: ✅ Active
- **Default**: `"sqlite:///kairix.db"`
- **Used in**: Test configurations
- **Notes**: New SQLite-based storage

## Frontend (Vite)

### VITE_API_URL
- **Purpose**: Backend API URL for frontend
- **Status**: ✅ Active
- **Default**: `"http://localhost:8888"`
- **Used in**: Multiple frontend components
- **Notes**: Must be prefixed with VITE_ for Vite to expose it

### VITE_KAIRIX_WEBSITE_PORT
- **Purpose**: Frontend development server port
- **Status**: ✅ Active
- **Default**: `5173`
- **Used in**: `kairix-website/src/lib/config.ts:10`

### VITE_HMR_HOST
- **Purpose**: Hot Module Replacement host for development
- **Status**: ✅ Active
- **Default**: `"localhost"`
- **Used in**: `kairix-website/vite.config.ts:17`

### VITE_ENABLE_CONTEXT_AWARENESS
- **Purpose**: Feature flag for context awareness
- **Status**: ❌ Inactive
- **Default**: `false`
- **Notes**: Defined but not currently used

### VITE_ENABLE_SENSOR_STREAMING
- **Purpose**: Feature flag for sensor data streaming
- **Status**: ❌ Inactive
- **Default**: `false`
- **Notes**: Defined but not currently used

### VITE_OPENAI_API_KEY
- **Purpose**: OpenAI API key for frontend (if needed)
- **Status**: ⚠️ Present but shouldn't be
- **Notes**: ⚠️ API keys should not be in frontend code

## Testing & Development

### TESTING
- **Purpose**: Flag to indicate test environment
- **Status**: ✅ Active
- **Default**: `"1"` (in test environments)
- **Used in**: Test configuration files

### PYTEST_CURRENT_TEST
- **Purpose**: Current pytest test identifier
- **Status**: ✅ Active (automatic)
- **Used in**: `kairix-offline/src/kairix_offline/ui/__init__.py:13`
- **Notes**: Set automatically by pytest

### CI
- **Purpose**: Continuous Integration environment flag
- **Status**: ✅ Active
- **Used in**: `kairix-website/playwright.config.ts`
- **Notes**: Set by CI systems (GitHub Actions, etc.)

### KAIRIX_DEBUG
- **Purpose**: Enable debug mode
- **Status**: ✅ Active
- **Default**: Not set (falsy)
- **Used in**: `kairix-offline/src/kairix_offline/ui/__init__.py:18`

## Platform-Specific

### Platform Selection
The system uses different configuration files based on the computing platform:
- `cpu.env` - CPU-only systems
- `cuda.env` - NVIDIA GPU systems
- `mps.env` - Apple Silicon Mac systems

Each sets appropriate values for:
- `KAIRIX_EMBEDDER_DEVICE`
- `KAIRIX_SUMMARIZER_DEVICE`
- Hardware-specific optimizations

## Security Recommendations

⚠️ **Critical**: Several API keys are currently exposed in configuration files:
1. `OPENAI_API_KEY`
2. `ELEVENLABS_API_KEY`
3. `BRAVE_API_KEY`
4. `VITE_OPENAI_API_KEY`

**Recommendations**:
1. Rotate all exposed API keys immediately
2. Use environment-specific secret management
3. Never commit API keys to version control
4. Consider using a secrets management service
5. Remove API keys from frontend code entirely

## Usage Patterns

1. **Required variables** use `get_or_raise()` utility function
2. **Optional variables** use `os.getenv()` with defaults
3. **Frontend variables** must be prefixed with `VITE_`
4. **Test environments** override many defaults for isolation
5. **Platform detection** automatically selects appropriate configurations