#!/usr/bin/env python3
"""
Token-aware Ollama client that prevents cutoffs
"""
import json
import requests
from typing import Optional
import tiktoken  # For token counting (OpenAI's tokenizer)

class TokenAwareOllamaClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        # Note: This uses OpenAI's tokenizer as approximation
        # Actual token count may vary by model
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except:
            print("Warning: tiktoken not installed. Install with: pip install tiktoken")
            self.encoder = None
    
    def count_tokens(self, text: str) -> int:
        """Approximate token count"""
        if self.encoder:
            return len(self.encoder.encode(text))
        else:
            # Rough approximation: 1 token ≈ 4 characters
            return len(text) // 4
    
    def generate_with_length_control(
        self,
        model: str,
        prompt: str,
        max_response_tokens: int = 500,
        total_context_limit: int = 4096,
        system: Optional[str] = None,
        **kwargs
    ):
        """Generate response with careful token management"""
        
        # Calculate prompt tokens
        prompt_tokens = self.count_tokens(prompt)
        if system:
            prompt_tokens += self.count_tokens(system)
        
        # Ensure we leave room for response
        if prompt_tokens + max_response_tokens > total_context_limit:
            # Adjust max response tokens
            available_tokens = total_context_limit - prompt_tokens - 100  # Safety margin
            if available_tokens < 100:
                raise ValueError(f"Prompt too long! Uses {prompt_tokens} tokens, leaving no room for response")
            max_response_tokens = min(max_response_tokens, available_tokens)
            print(f"Adjusted max_response_tokens to {max_response_tokens} due to prompt length")
        
        # Prepare request
        data = {
            "model": model,
            "prompt": prompt,
            "options": {
                "num_predict": max_response_tokens,
                "num_ctx": total_context_limit,
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
                "stop": kwargs.get("stop", [])
            },
            "stream": kwargs.get("stream", True)
        }
        
        if system:
            data["system"] = system
        
        # Send request
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=data,
            stream=data.get("stream", True)
        )
        
        # Handle response
        if data.get("stream", True):
            return self._handle_stream(response, max_response_tokens)
        else:
            return response.json()
    
    def _handle_stream(self, response, max_tokens):
        """Handle streaming response with token counting"""
        full_response = ""
        token_count = 0
        
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if "response" in chunk:
                    chunk_text = chunk["response"]
                    full_response += chunk_text
                    
                    # Approximate token count
                    token_count = self.count_tokens(full_response)
                    
                    # Warn if approaching limit
                    if token_count > max_tokens * 0.9:
                        print(f"\nWarning: Approaching token limit ({token_count}/{max_tokens})")
                    
                    yield chunk
        
        print(f"\nTotal response tokens: ~{token_count}")

# Usage examples
if __name__ == "__main__":
    client = TokenAwareOllamaClient()
    
    # Example 1: Short response
    print("=== Example 1: Short Response ===")
    for chunk in client.generate_with_length_control(
        model="mistral-7b-merged",
        prompt="What is Python?",
        max_response_tokens=100,  # Very short response
        temperature=0.5
    ):
        if "response" in chunk:
            print(chunk["response"], end="", flush=True)
    
    print("\n\n=== Example 2: Controlled Length ===")
    # Example 2: Longer but controlled
    for chunk in client.generate_with_length_control(
        model="mistral-7b-merged",
        prompt="Explain the key features of Python programming language",
        max_response_tokens=300,  # Medium response
        system="Be concise and use bullet points.",
        temperature=0.7
    ):
        if "response" in chunk:
            print(chunk["response"], end="", flush=True)
    
    print("\n\n=== Example 3: Length with Stop Sequences ===")
    # Example 3: Using stop sequences
    for chunk in client.generate_with_length_control(
        model="mistral-7b-merged",
        prompt="List 3 benefits of exercise",
        max_response_tokens=500,
        stop=["\n\n", "In conclusion", "Finally"],  # Stop at these sequences
        temperature=0.7
    ):
        if "response" in chunk:
            print(chunk["response"], end="", flush=True)