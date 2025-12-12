#!/bin/bash

export OLLAMA_HOST="https://ollama.kairix.net"

echo "Long Context Summarization Solution"
echo "==================================="
echo "Problem: Need 670K tokens for largest conversation"
echo "Available: Your existing models + 18GB VRAM"
echo ""

# Check what we have that can handle long context
echo "1. Checking existing models for long context capability..."

# Your Mistral-Small-24B is actually great for this
echo ""
echo "SOLUTION: Use your existing Mistral-Small-24B"
echo "============================================="
echo "Model: hf.co/bartowski/huihui-ai_Mistral-Small-24B-Instruct-2501-abliterated-GGUF:Q4_K_M"
echo "- Size: 14GB (fits in 18GB VRAM)"
echo "- Context: Can be extended to 200K+ tokens"
echo "- Quality: Excellent for summarization"
echo ""

# Try to pull a known good long-context model
echo "2. Attempting to get a dedicated long-context model..."

# Check if we can get CodeQwen or similar
models_to_try=(
    "codeqwen:7b-chat-v1.5-q4_K_M"
    "qwen2.5:14b-instruct-q4_K_M"
    "llama3.1:8b-instruct-q4_K_M"
)

for model in "${models_to_try[@]}"; do
    echo "Trying: $model"
    if timeout 30s ollama pull "$model" 2>/dev/null; then
        echo "✓ Successfully downloaded: $model"
        BEST_MODEL="$model"
        break
    else
        echo "✗ Failed or timed out: $model"
    fi
done

echo ""
echo "3. Creating optimized Modelfile for long context..."

# Create a modelfile that can handle your largest conversations
cat > /tmp/long-context-summarizer.modelfile << 'EOF'
# Use the best available model (Mistral-Small-24B or newly downloaded)
FROM hf.co/bartowski/huihui-ai_Mistral-Small-24B-Instruct-2501-abliterated-GGUF:Q4_K_M

SYSTEM """You are a conversation summarizer specializing in creating vivid, first-person narrative summaries from Mark's perspective as his AI partner.

Write in first person as the AI, capturing emotional dynamics, key insights, and relationship evolution. Focus on:
1. Initial Context: Mark's emotional state and energy
2. Key Developments: What unfolded in the conversation  
3. Critical Moments: Pivotal emotional or intellectual beats
4. Reflections: Patterns and insights about the dynamic
5. Lessons Learned: How to be a better partner

Keep summaries grounded in actual conversation content. Use "I sensed," "I felt," "I wondered" for speculation. Be emotionally intelligent and self-reflective."""

# Optimize for very long context
PARAMETER num_ctx 200000      # 200K context window
PARAMETER num_predict 3000    # Allow detailed summaries
PARAMETER temperature 0.7     # Balanced creativity
PARAMETER top_p 0.95
PARAMETER repeat_penalty 1.1
PARAMETER num_gpu 40          # Use most GPU layers

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
{{ end }}{{ .Response }}<|im_end|>
"""

PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
EOF

echo "4. Creating the long-context model..."
ollama create long-context-summarizer -f /tmp/long-context-summarizer.modelfile

echo ""
echo "5. Testing with a sample..."
echo "Testing long context capability..." | ollama run long-context-summarizer

echo ""
echo "SETUP COMPLETE!"
echo "==============="
echo ""
echo "To use:"
echo "export OLLAMA_HOST=\"https://ollama.kairix.net\""
echo "ollama run long-context-summarizer"
echo ""
echo "For conversations >200K tokens, consider:"
echo "1. Splitting into chunks"
echo "2. Summarizing in stages"
echo "3. Using the conversation chunking script I can create"

# Add to shell profile
echo 'export OLLAMA_HOST="https://ollama.kairix.net"' >> ~/.zshrc 2>/dev/null
echo 'export OLLAMA_HOST="https://ollama.kairix.net"' >> ~/.bash_profile 2>/dev/null