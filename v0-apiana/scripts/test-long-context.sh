#!/bin/bash

export OLLAMA_HOST="https://ollama.kairix.net"

echo "Testing Long Context Summarizer"
echo "=============================="
echo ""

# Test with a medium-sized conversation first (350K tokens)
test_file="/Users/mark/apiana-ai/output/test-run-1/parsed/66_retail_frustration_rant.json"

if [ -f "$test_file" ]; then
    echo "Testing with: 66_retail_frustration_rant.json (~350K tokens)"
    echo "This should fit within our 200K context window after truncation"
    echo ""
    
    # Extract just the conversation content for summarization
    echo "Extracting conversation content..."
    
    # Create a temporary file with just the essential content
    jq -r '.messages[] | select(.author.role != null) | "\(.author.role): \(.content.parts[0])"' "$test_file" > /tmp/conversation_content.txt
    
    # Check the size
    echo "Conversation content size:"
    wc -c /tmp/conversation_content.txt
    
    # Estimate tokens
    chars=$(wc -c < /tmp/conversation_content.txt)
    tokens=$((chars / 4))
    echo "Estimated tokens: $tokens"
    
    if [ $tokens -lt 180000 ]; then
        echo ""
        echo "✓ Size is good for testing. Sending to summarizer..."
        echo ""
        
        # Create the prompt
        cat > /tmp/summarize_prompt.txt << 'EOF'
Please create a vivid, first-person narrative summary of this conversation from your perspective as Mark's AI partner. Focus on the emotional dynamics, key insights, and relationship evolution.

Here's the conversation:
EOF
        
        # Add the conversation content
        cat /tmp/conversation_content.txt >> /tmp/summarize_prompt.txt
        
        # Send to the model
        cat /tmp/summarize_prompt.txt | ollama run long-context-summarizer
        
    else
        echo "⚠️  Still too large, will need chunking strategy"
    fi
    
else
    echo "Test file not found. Available files:"
    ls -la /Users/mark/apiana-ai/output/test-run-1/parsed/*.json | head -5
fi

echo ""
echo "Test complete!"