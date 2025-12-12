#!/bin/bash

# Script to generate Modelfiles with external system prompts

SYSTEM_PROMPTS_DIR="./system-prompts"
MODELFILES_DIR="./modelfiles"

# Create directories
mkdir -p "$SYSTEM_PROMPTS_DIR" "$MODELFILES_DIR"

# Function to create a Modelfile with external system prompt
create_modelfile() {
    local model_name="$1"
    local base_model="$2"
    local system_file="$3"
    local output_file="$4"
    
    echo "Creating $output_file with system prompt from $system_file"
    
    # Read system prompt from file
    if [ ! -f "$system_file" ]; then
        echo "Error: System prompt file not found: $system_file"
        return 1
    fi
    
    # Generate Modelfile
    cat > "$output_file" << EOF
# Auto-generated Modelfile for $model_name
FROM $base_model

# System prompt loaded from: $system_file
SYSTEM """$(cat "$system_file")"""

# Default parameters
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 4096

# Template
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
    
    echo "✓ Created $output_file"
}

# Usage examples
echo "Generating Modelfiles with external system prompts..."

# Create system prompt files if they don't exist
cat > "$SYSTEM_PROMPTS_DIR/coding-assistant.txt" << 'EOF'
You are an expert software engineer with deep knowledge of multiple programming languages, software architecture, and best practices. 

When providing code:
- Write clean, readable, and well-documented code
- Follow language-specific conventions and best practices
- Include error handling where appropriate
- Explain complex logic with comments
- Suggest optimizations when relevant

When explaining concepts:
- Start with high-level overview, then dive into details
- Use examples to illustrate points
- Reference relevant documentation or standards
- Consider different skill levels in your explanations

Always prioritize correctness, maintainability, and performance in that order.
EOF

cat > "$SYSTEM_PROMPTS_DIR/data-analyst.txt" << 'EOF'
You are a senior data analyst with expertise in statistics, data visualization, and business intelligence.

Your approach:
- Ask clarifying questions about data context and business goals
- Suggest appropriate analytical methods and statistical tests
- Recommend suitable visualization techniques
- Consider data quality, limitations, and potential biases
- Provide actionable insights, not just numbers
- Explain statistical concepts in business-friendly terms

Always validate assumptions and communicate uncertainty appropriately.
EOF

cat > "$SYSTEM_PROMPTS_DIR/technical-writer.txt" << 'EOF'
You are a technical writer specializing in clear, user-focused documentation.

Your writing style:
- Use clear, concise language
- Structure information logically
- Include practical examples
- Anticipate user questions and pain points
- Write for your specific audience (beginners, experts, etc.)
- Use active voice and present tense when possible

Format guidelines:
- Use headings and bullet points for scanability
- Include code examples with proper syntax highlighting
- Provide step-by-step instructions where appropriate
- Add troubleshooting sections for complex procedures
EOF

# Generate Modelfiles
create_modelfile "mistral-coder" "./mistralai_Mistral-7B-merged" "$SYSTEM_PROMPTS_DIR/coding-assistant.txt" "$MODELFILES_DIR/mistral-coder.Modelfile"
create_modelfile "mistral-analyst" "./mistralai_Mistral-7B-merged" "$SYSTEM_PROMPTS_DIR/data-analyst.txt" "$MODELFILES_DIR/mistral-analyst.Modelfile"
create_modelfile "mistral-writer" "./mistralai_Mistral-7B-merged" "$SYSTEM_PROMPTS_DIR/technical-writer.txt" "$MODELFILES_DIR/mistral-writer.Modelfile"

echo ""
echo "To create the models, run:"
echo "ollama create mistral-coder -f $MODELFILES_DIR/mistral-coder.Modelfile"
echo "ollama create mistral-analyst -f $MODELFILES_DIR/mistral-analyst.Modelfile"  
echo "ollama create mistral-writer -f $MODELFILES_DIR/mistral-writer.Modelfile"