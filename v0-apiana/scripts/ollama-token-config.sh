#!/bin/bash

# Example: Proper token configuration for Ollama

# num_predict = max tokens to generate in response
# num_ctx = total context window (prompt + response)

# Short response example
curl http://localhost:11434/api/generate -d '{
  "model": "mistral-7b-merged",
  "prompt": "Explain quantum computing in simple terms",
  "options": {
    "num_predict": 150,      # Max 150 tokens for response
    "num_ctx": 2048,         # Total context window
    "temperature": 0.7
  },
  "stream": false
}'

# Longer response with larger context
curl http://localhost:11434/api/generate -d '{
  "model": "mistral-7b-merged",
  "prompt": "Write a detailed guide on Python decorators",
  "options": {
    "num_predict": 1000,     # Max 1000 tokens for response
    "num_ctx": 4096,         # Larger context window
    "temperature": 0.7
  }
}'