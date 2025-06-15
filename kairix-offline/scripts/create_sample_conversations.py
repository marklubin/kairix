#!/usr/bin/env python3
"""Create sample conversation files for testing the ingestion cron job"""

import json
import os
from datetime import datetime

# Sample conversation data
sample_conversations = [
    {
        "id": "conv1",
        "messages": [
            {
                "role": "user",
                "content": "What is the capital of France?"
            },
            {
                "role": "assistant", 
                "content": "The capital of France is Paris. Paris is not only the capital but also the largest city in France, known for its iconic landmarks like the Eiffel Tower, Louvre Museum, and Notre-Dame Cathedral."
            },
            {
                "role": "user",
                "content": "Tell me more about the Eiffel Tower"
            },
            {
                "role": "assistant",
                "content": "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris. It was built from 1887 to 1889 as the entrance arch for the 1889 World's Fair. Standing at 324 meters tall, it was the tallest man-made structure in the world until 1930."
            }
        ],
        "timestamp": datetime.now().isoformat()
    },
    {
        "id": "conv2", 
        "messages": [
            {
                "role": "user",
                "content": "How do I implement a binary search in Python?"
            },
            {
                "role": "assistant",
                "content": "Here's how to implement binary search in Python:\n\n```python\ndef binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    \n    while left <= right:\n        mid = (left + right) // 2\n        \n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    \n    return -1  # Element not found\n```\n\nThis algorithm works on sorted arrays and has O(log n) time complexity."
            }
        ],
        "timestamp": datetime.now().isoformat()
    }
]

def main():
    # Create directory if it doesn't exist
    output_dir = "./data/chat_logs"
    os.makedirs(output_dir, exist_ok=True)
    
    # Write sample files
    for i, conv in enumerate(sample_conversations):
        filename = f"conversation_{datetime.now().strftime('%Y%m%d')}_{i+1}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(conv, f, indent=2)
        
        print(f"Created: {filepath}")
    
    print(f"\nCreated {len(sample_conversations)} sample conversation files in {output_dir}")

if __name__ == "__main__":
    main()