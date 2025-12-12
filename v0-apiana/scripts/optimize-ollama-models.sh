#!/bin/bash

export OLLAMA_HOST="https://ollama.kairix.net"

echo "Optimizing Ollama Models for Long Context Summarization"
echo "======================================================="

# Remove models older than 1 month (2+ months shown in list)
echo "1. Removing old models (2+ months unused)..."

models_to_remove=(
    "cele:latest"
    "enceledus/phi4:latest" 
    "zac/phi4-tools:latest"
    "mistral-nemo:latest"
    "orca2:13b"
)

for model in "${models_to_remove[@]}"; do
    echo "Removing: $model"
    ollama rm "$model" 2>/dev/null || echo "  (already removed or error)"
done

echo ""
echo "2. Checking available space after cleanup..."
ollama list

echo ""
echo "3. Downloading optimal model for 670K+ context..."
echo ""

# Best option: Yi-34B with 200K context, fits well in 18GB
echo "Downloading Yi-34B-200K (200K context, ~12GB VRAM)..."
echo "This is the best option for your 670K token requirement."

# Check if Yi model is available
if ollama list | grep -q "yi:"; then
    echo "Yi model variants already available, checking..."
    ollama list | grep "yi:"
else
    echo "Attempting to pull Yi-34B-200K..."
    ollama pull yi:34b-200k-instruct-q4_K_M 2>/dev/null || {
        echo "Yi model not available, trying alternative..."
        
        # Alternative: Qwen2.5 which has excellent long context
        echo "Downloading Qwen2.5-72B (128K native, extends to 1M+)..."
        ollama pull qwen2.5:72b-instruct-q4_K_M 2>/dev/null || {
            echo "Qwen2.5-72B not available, trying smaller Qwen..."
            ollama pull qwen2.5:32b-instruct-q4_K_M 2>/dev/null || {
                echo "Trying Qwen2.5-14B as fallback..."
                ollama pull qwen2.5:14b-instruct-q4_K_M
            }
        }
    }
fi

echo ""
echo "4. Current models after optimization:"
ollama list

echo ""
echo "5. Setting up environment variable for your shell..."
echo 'export OLLAMA_HOST="https://ollama.kairix.net"' >> ~/.zshrc
echo 'export OLLAMA_HOST="https://ollama.kairix.net"' >> ~/.bashrc

echo ""
echo "6. Creating Modelfile for long-context summarizer..."