#!/bin/bash

# Start Ollama with debug logging
echo "Starting Ollama with debug logging..."
echo "Logs will show all API requests including prompts"
echo ""

# Set debug environment variable and start ollama
OLLAMA_DEBUG=1 ollama serve