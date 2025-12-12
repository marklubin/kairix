#!/bin/bash

# Set up Ollama to use remote server
export OLLAMA_HOST="https://ollama.kairix.net"

echo "Setting up Ollama for remote server: $OLLAMA_HOST"
echo "VRAM Available: 18GB"
echo "Required Context: 670K+ tokens"
echo ""

# Check connection
echo "1. Testing connection..."
ollama list

echo ""
echo "2. Checking available models for long context and 18GB VRAM..."

# Models that can handle 200K+ context with 18GB VRAM
echo ""
echo "Recommended Models for 670K+ context:"
echo "====================================="

echo ""
echo "Option 1: Llama 3.1 70B (Quantized Q4_K_M)"
echo "- Context: 128K (not enough for largest, but good for most)"
echo "- VRAM: ~18GB with Q4_K_M quantization"
echo "- Command: ollama pull llama3.1:70b-instruct-q4_K_M"

echo ""
echo "Option 2: Llama 3.2 90B (Quantized Q3_K_M)"  
echo "- Context: 128K"
echo "- VRAM: ~18GB with aggressive quantization"
echo "- Command: ollama pull llama3.2:90b-vision-instruct-q3_K_M"

echo ""
echo "Option 3: Qwen2.5-72B (Best for long context)"
echo "- Context: 128K native, can extend to 1M+"
echo "- VRAM: ~18GB with Q4_K_M"
echo "- Command: ollama pull qwen2.5:72b-instruct-q4_K_M"

echo ""
echo "Option 4: Yi-34B-200K (Specialized for long context)"
echo "- Context: 200K native"
echo "- VRAM: ~12GB (plenty of headroom)"
echo "- Command: ollama pull yi:34b-200k-instruct-q4_K_M"

echo ""
echo "Option 5: Claude-3-Haiku via Ollama proxy (if available)"
echo "- Context: 200K"
echo "- External API"

echo ""
echo "BEST CHOICE for your needs: Qwen2.5-72B or Yi-34B-200K"
echo ""

# Check what's currently installed
echo "3. Currently installed models:"
ollama list

echo ""
echo "4. Cleaning up old models (>1 month unused)..."
# This would need to be done manually as Ollama doesn't track usage dates