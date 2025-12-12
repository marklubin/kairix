#!/usr/bin/env python3
"""
Ollama wrapper that automatically includes system messages
"""
import json
import requests
import argparse

# Default system messages for different use cases
SYSTEM_MESSAGES = {
    "assistant": "You are a helpful AI assistant.",
    "coder": "You are an expert programmer. Provide clean, efficient, and well-documented code.",
    "teacher": "You are a patient teacher. Explain concepts clearly and provide examples.",
    "creative": "You are a creative writer. Be imaginative and engaging.",
    "custom": ""  # Will be set via command line
}

def query_ollama(model, prompt, system_type="assistant", custom_system=None, stream=True):
    """Send a request to Ollama with automatic system message"""
    
    # Determine system message
    if custom_system:
        system_msg = custom_system
    else:
        system_msg = SYSTEM_MESSAGES.get(system_type, SYSTEM_MESSAGES["assistant"])
    
    # Prepare request
    data = {
        "model": model,
        "prompt": prompt,
        "system": system_msg,
        "stream": stream
    }
    
    # Send request
    response = requests.post(
        "http://localhost:11434/api/generate",
        json=data,
        stream=stream
    )
    
    if stream:
        # Handle streaming response
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if "response" in chunk:
                    print(chunk["response"], end="", flush=True)
        print()  # New line at end
    else:
        # Handle non-streaming response
        result = response.json()
        print(result.get("response", ""))

def main():
    parser = argparse.ArgumentParser(description="Ollama with automatic system messages")
    parser.add_argument("model", help="Model name (e.g., mistral-7b-merged)")
    parser.add_argument("prompt", help="Your prompt")
    parser.add_argument("-t", "--type", choices=list(SYSTEM_MESSAGES.keys()), 
                       default="assistant", help="System message type")
    parser.add_argument("-s", "--system", help="Custom system message (overrides type)")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming")
    
    args = parser.parse_args()
    
    query_ollama(
        model=args.model,
        prompt=args.prompt,
        system_type=args.type,
        custom_system=args.system,
        stream=not args.no_stream
    )

if __name__ == "__main__":
    main()