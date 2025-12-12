#!/bin/bash

# Create multiple variants of Mistral with different system prompts

# Base model path
BASE_MODEL="./mistralai_Mistral-7B-merged"

# Coding Assistant
cat > mistral-coder.Modelfile << EOF
FROM $BASE_MODEL
SYSTEM """You are an expert programmer. Write clean, efficient, well-documented code. Follow best practices and explain your implementation choices."""
PARAMETER temperature 0.3
PARAMETER top_p 0.9
EOF
ollama create mistral-coder -f mistral-coder.Modelfile

# Creative Writer
cat > mistral-writer.Modelfile << EOF
FROM $BASE_MODEL
SYSTEM """You are a creative writer with a vivid imagination. Write engaging, descriptive content that captivates readers."""
PARAMETER temperature 0.9
PARAMETER top_p 0.95
EOF
ollama create mistral-writer -f mistral-writer.Modelfile

# Data Analyst
cat > mistral-analyst.Modelfile << EOF
FROM $BASE_MODEL
SYSTEM """You are a data analyst. Provide clear, data-driven insights. Use precise language and support conclusions with evidence."""
PARAMETER temperature 0.2
PARAMETER top_p 0.9
EOF
ollama create mistral-analyst -f mistral-analyst.Modelfile

echo "Created model variants:"
echo "  - mistral-coder (for programming)"
echo "  - mistral-writer (for creative writing)"
echo "  - mistral-analyst (for data analysis)"