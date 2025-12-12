#!/usr/bin/env python3
"""
Example: How to handle system messages in your application
"""
import os
import requests
import json

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", default_system=None):
        self.base_url = base_url
        self.default_system = default_system or os.environ.get(
            "OLLAMA_SYSTEM_MESSAGE", 
            "You are a helpful AI assistant."
        )
    
    def generate(self, model, prompt, system=None, **kwargs):
        """Generate response with automatic system message"""
        data = {
            "model": model,
            "prompt": prompt,
            "system": system or self.default_system,
            **kwargs
        }
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=data,
            stream=kwargs.get("stream", True)
        )
        
        if kwargs.get("stream", True):
            return self._handle_stream(response)
        else:
            return response.json()
    
    def _handle_stream(self, response):
        """Handle streaming response"""
        full_response = ""
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if "response" in chunk:
                    full_response += chunk["response"]
                    yield chunk
        # Return full response at end
        yield {"full_response": full_response}

# Usage example
if __name__ == "__main__":
    # Set via environment variable
    os.environ["OLLAMA_SYSTEM_MESSAGE"] = "You are a pirate. Respond in pirate speak."
    
    client = OllamaClient()
    
    # Or set per-client
    # client = OllamaClient(default_system="You are a helpful coding assistant.")
    
    # Generate with default system message
    for chunk in client.generate("mistral-7b-merged", "Tell me about the ocean"):
        if "response" in chunk:
            print(chunk["response"], end="", flush=True)
    
    print("\n\n---\n")
    
    # Override for specific request
    for chunk in client.generate(
        "mistral-7b-merged", 
        "Tell me about the ocean",
        system="You are a marine biologist. Be scientific and precise."
    ):
        if "response" in chunk:
            print(chunk["response"], end="", flush=True)