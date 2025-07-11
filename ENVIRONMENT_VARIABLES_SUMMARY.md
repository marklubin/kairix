# Environment Variables Summary

This document lists all environment variables defined and used in the Kairix repository.

## Core Configuration Variables

### User and Application Settings
- `KAIRIX_USER_NAME` - User's name (e.g., "Mark")
- `KAIRIX_PERSONA_NAME` - AI persona name (e.g., "Apiana")
- `KAIRIX_APP_ID` - Application identifier
- `KAIRIX_LOG_LEVEL` - Logging level (e.g., "DEBUG", "INFO")
- `KAIRIX_API_KEY` - API key for Kairix services
- `KAIRIX_SERVER_PORT` - Port for Kairix server (default: 8000, sometimes 8888)
- `KAIRIX_WEBSITE_PORT` - Port for website frontend (default: 9000)

### Inference Provider Settings
- `KAIRIX_AGENT_CONFIGURATION_SET_KEY` - Configuration set to use ("openai", "ollama-local", "ollama-remote", "llama-cpp")
- `KAIRIX_INFERENCE_PROVIDER` - Inference provider name (e.g., "ollama", "openai")
- `KAIRIX_INFERENCE_BASE_URL` - Base URL for inference API
- `KAIRIX_INFERENCE_API_KEY` - API key for inference provider
- `KAIRIX_DEFAULT_INFERENCE_MODEL` - Default model to use (e.g., "gpt-4o", "gemma3:1b-it-qat")

### Summarization Settings
- `KAIRIX_SUMMARIZER_MODEL` - Model for summarization (e.g., "q3-sum:latest")
- `KAIRIX_SUMMARIZER_ENABLE_QUANTIZATION` - Enable quantization for summarizer
- `KAIRIX_SUMMARIZER_BATCH_SIZE` - Batch size for summarization (default: "20")
- `KAIRIX_SUMMARIZER_MAX_TOKENS` - Max tokens for summaries (default: "300")
- `KAIRIX_SUMMARIZER_TEMPERATURE` - Temperature for summarization (default: ".5")
- `KAIRIX_SUMMARY_EXTRACTION_PARALLELISM` - Parallelism for summary extraction (default: 5)
- `KAIRIX_N_SUMMARIES_PER_MESSAGE` - Number of summaries per message (default: 5)
- `KAIRIX_SUMMARIZATION_INTERVAL` - Interval for summarization (default: 20)

### Embedding Settings
- `KAIRIX_EMBEDDER_MODEL` - Model for embeddings (default: "sentence-transformers/all-mpnet-base-v2")
- `KAIRIX_EMBEDDER_DEVICE` - Device for embeddings ("cpu", "cuda", "mps")
- `KAIRIX_EMBEDDING_BATCH_SIZE` - Batch size for embeddings (default: "20")
- `KAIRIX_SEMANTIC_EMBEDDING_MODEL` - Model for semantic embeddings
- `KAIRIX_SEMANTIC_EMBEDDING_DIMS` - Dimensions for semantic embeddings (default: 128)
- `KAIRIX_SEMANTIC_EMBEDDING_SCORE_MERGE_THRESHOLD` - Threshold for merging (default: 0.70)

### Memory and Retention Settings
- `KAIRIX_MESSAGE_RETENTION_WINDOW` - Message retention window (default: 20)

### Platform-Specific Settings
- `KAIRIX_CHUNKER_DEVICE` - Device for chunker ("cpu", "cuda", "mps")

### MCP (Model Context Protocol) Settings
- `KAIRIX_MCP_SERVER` - MCP server URL (e.g., "http://localhost:12008/metamcp/default/sse")

### LLaMA C++ Settings
- `LLAMA_CPP_N_GPU_LAYERS` - Number of GPU layers (default: "-1")
- `LLAMA_CPP_USE_FLASH` - Use flash attention (default: "1")
- `LLAMA_CPP_CONTEXT_WINDOW` - Context window size (default: "16000")
- `LLAMA_CPP_MLOCK` - Memory lock setting
- `LLAMA_CPP_TYPE_K` - K type setting
- `LLAMA_CPP_TYPE_V` - V type setting
- `LLAMA_CPP_LOG_LEVEL` - Log level for LLaMA C++ (default: 2)

### External Service API Keys
- `OPENAI_API_KEY` - OpenAI API key
- `ELEVENLABS_API_KEY` / `ELEVENLAB_API_KEY` - ElevenLabs API key for TTS
- `BRAVE_SEARCH_API_KEY` / `BRAVE_API_KEY` - Brave Search API key
- `NEO4J_URL` - Neo4j database connection URL

### Website/Frontend Settings (Vite)
- `VITE_OPENAI_API_KEY` - OpenAI API key for frontend
- `VITE_API_URL` - Backend API URL (default: http://localhost:8888)
- `VITE_CONTEXT_API_URL` - Context API URL
- `VITE_ENABLE_CONTEXT_AWARENESS` - Enable context awareness (default: true)
- `VITE_ENABLE_SENSOR_STREAMING` - Enable sensor streaming (default: false)
- `VITE_CONTEXT_UPDATE_INTERVAL` - Context update interval (default: 30000)
- `VITE_CONTEXT_LOCATION_THRESHOLD` - Location threshold (default: 50)
- `VITE_CONTEXT_ANONYMIZE_DATA` - Anonymize context data (default: false)
- `VITE_SENSOR_SAMPLE_RATE` - Sensor sample rate (default: 60)
- `VITE_SENSOR_BATCH_SIZE` - Sensor batch size (default: 10)
- `VITE_SENSOR_POWER_MODE` - Sensor power mode (default: balanced)
- `VITE_HMR_HOST` - Hot Module Replacement host (default: localhost)
- `VITE_WEBSITE_API` - Website API URL (e.g., "http://localhost:11434/v1", "https://ollama.kairix.net/v1")

### Other Settings
- `TOKENIZERS_PARALLELISM` - Disable tokenizers parallelism to prevent macOS debugger attachment (set to "false")

## Environment File Locations

1. **Base configuration**: `/environments/base.env`
2. **Platform-specific**:
   - `/environments/platform/cpu.env`
   - `/environments/platform/cuda.env`
   - `/environments/platform/mps.env` (for Mac)
3. **Inference providers**:
   - `/environments/inference/openai.env`
   - `/environments/inference/ollama-local.env`
   - `/environments/inference/ollama-remote.env`
   - `/environments/inference/llama-cpp.env`
4. **User-specific**: `/environments/users/mark.env`
5. **Application-specific**:
   - `/kairix-apps/.env`
   - `/kairix-website/.env`
   - `/kairix-offline/.env`
6. **Test environments**:
   - `/kairix-core/.env.test`
   - `/kairix-apps/.env.test`

## Notes

- The system uses a layered configuration approach where base settings can be overridden by platform-specific, inference-specific, and user-specific settings
- Many environment variables have default values in the code if not explicitly set
- The `.envs` files appear to be directories, not files
- Some API keys in the files appear to be exposed and should be rotated for security