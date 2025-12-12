#!/usr/bin/env python3
"""
Calculate token requirements for conversation files
"""
import json
import os
from pathlib import Path

def estimate_tokens(text):
    """Rough token estimation: ~4 characters per token"""
    return len(text) // 4

def analyze_conversation_file(file_path):
    """Analyze a single conversation file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Convert back to string to get total size
    content = json.dumps(data, indent=2)
    
    return {
        'file': file_path.name,
        'characters': len(content),
        'estimated_tokens': estimate_tokens(content),
        'message_count': len(data.get('messages', [])),
        'title': data.get('title', 'Unknown')
    }

# Analyze the largest files
files_to_check = [
    '/Users/mark/apiana-ai/output/test-run-1/parsed/233_unmatched_hinge_conversation_history.json',
    '/Users/mark/apiana-ai/output/test-run-1/parsed/66_retail_frustration_rant.json',
    '/Users/mark/apiana-ai/output/test-run-1/parsed/201_understanding_action_paralysis.json',
    '/Users/mark/apiana-ai/output/test-run-1/parsed/48_deflecting_room_questions.json',
    '/Users/mark/apiana-ai/output/test-run-1/parsed/292_user_expresses_frustration.json'
]

print("Token Analysis for Largest Conversations")
print("=" * 50)

results = []
for file_path in files_to_check:
    if os.path.exists(file_path):
        result = analyze_conversation_file(Path(file_path))
        results.append(result)
        print(f"\nFile: {result['file']}")
        print(f"Title: {result['title']}")
        print(f"Characters: {result['characters']:,}")
        print(f"Estimated Tokens: {result['estimated_tokens']:,}")
        print(f"Messages: {result['message_count']}")

# Find the largest
if results:
    largest = max(results, key=lambda x: x['estimated_tokens'])
    print("\n" + "=" * 50)
    print("LARGEST CONVERSATION:")
    print(f"File: {largest['file']}")
    print(f"Estimated Tokens: {largest['estimated_tokens']:,}")
    
    # Calculate required context window
    system_prompt_tokens = 2000  # Approximate for your system prompt
    safety_margin = 1000        # Safety margin
    response_tokens = 2000      # Response space
    
    required_ctx = largest['estimated_tokens'] + system_prompt_tokens + safety_margin + response_tokens
    
    print("\nContext Window Requirements:")
    print(f"Conversation: {largest['estimated_tokens']:,} tokens")
    print(f"System Prompt: {system_prompt_tokens:,} tokens")
    print(f"Response Space: {response_tokens:,} tokens")
    print(f"Safety Margin: {safety_margin:,} tokens")
    print(f"TOTAL REQUIRED: {required_ctx:,} tokens")
    
    # Recommend context windows
    print(f"\nRecommended minimum context window: {required_ctx:,} tokens")
    if required_ctx <= 32768:
        print("✓ 32K context window should work")
    elif required_ctx <= 65536:
        print("✓ 64K context window needed")
    elif required_ctx <= 131072:
        print("✓ 128K context window needed")
    else:
        print("⚠️  Need 200K+ context window or split conversation")