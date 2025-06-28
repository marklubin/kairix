"""Example client code showing how to use the Kairix OpenAI-compatible API."""

import openai
import asyncio
import httpx


def test_non_streaming():
    """Test non-streaming chat completion."""
    # Configure OpenAI client to point to local Kairix API
    client = openai.OpenAI(
        api_key="not-needed",  # API key not required for local instance
        base_url="http://localhost:8000/v1"
    )
    
    # Send a chat completion request - the response will be a real OpenAI ChatCompletion object
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Hello! Tell me about yourself."}
        ],
        temperature=0.7,
        max_tokens=150
    )
    
    print("Non-streaming response:")
    print(f"Response type: {type(response)}")  # openai.types.chat.ChatCompletion
    print(f"Content: {response.choices[0].message.content}")
    print(f"Model: {response.model}")
    print(f"Usage: {response.usage}")
    print("\n" + "="*50 + "\n")


async def test_streaming():
    """Test streaming chat completion."""
    # Configure async client
    client = openai.AsyncOpenAI(
        api_key="not-needed",
        base_url="http://localhost:8000/v1",
        http_client=httpx.AsyncClient()
    )
    
    # Send streaming request - will receive real OpenAI ChatCompletionChunk objects
    stream = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "What's the weather like today?"},
            {"role": "assistant", "content": "I'll check the current conditions for you."},
            {"role": "user", "content": "Thanks! Also, what time is it?"}
        ],
        stream=True
    )
    
    print("Streaming response:")
    print("Chunk types will be: openai.types.chat.ChatCompletionChunk")
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end='', flush=True)
    print("\n")


def test_list_models():
    """Test listing available models."""
    client = openai.OpenAI(
        api_key="not-needed",
        base_url="http://localhost:8000/v1"
    )
    
    # Note: models.list() returns a raw response, not typed objects
    models = client.models.list()
    print("Available models:")
    for model in models:
        print(f"  - {model.id} (owned by: {model.owned_by})")
    print()


def test_conversation_with_history():
    """Test a multi-turn conversation."""
    client = openai.OpenAI(
        api_key="not-needed",
        base_url="http://localhost:8000/v1"
    )
    
    messages = [
        {"role": "user", "content": "My name is Alice and I love machine learning."},
        {"role": "assistant", "content": "Nice to meet you, Alice! Machine learning is a fascinating field."},
        {"role": "user", "content": "What do you remember about me?"}
    ]
    
    response = client.chat.completions.create(
        model="gpt-4",  # Uses the "advanced" persona
        messages=messages,
        user="alice"  # Optional user identifier
    )
    
    print("Conversation with history:")
    print(f"Response: {response.choices[0].message.content}")
    print(f"Finish reason: {response.choices[0].finish_reason}")
    print()


def test_multipart_content():
    """Test sending multipart content (text + image references)."""
    client = openai.OpenAI(
        api_key="not-needed",
        base_url="http://localhost:8000/v1"
    )
    
    # OpenAI supports multipart content in messages
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What do you see in this"},
                    {"type": "text", "text": " image?"},
                    # Note: Kairix currently extracts only text parts
                    {"type": "image_url", "image_url": {"url": "http://example.com/image.jpg"}}
                ]
            }
        ]
    )
    
    print("Multipart content handling:")
    print(f"Response: {response.choices[0].message.content}")
    print()


def demonstrate_type_safety():
    """Demonstrate that we're using real OpenAI types."""
    client = openai.OpenAI(
        api_key="not-needed",
        base_url="http://localhost:8000/v1"
    )
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hi"}]
    )
    
    # All these are real OpenAI types with proper typing
    from openai.types.chat import ChatCompletion, ChatCompletionMessage
    from openai.types import CompletionUsage
    
    assert isinstance(response, ChatCompletion)
    assert isinstance(response.choices[0].message, ChatCompletionMessage)
    assert isinstance(response.usage, CompletionUsage)
    
    print("Type safety demonstration:")
    print(f"✓ Response is a real ChatCompletion: {isinstance(response, ChatCompletion)}")
    print(f"✓ Message is a real ChatCompletionMessage: {isinstance(response.choices[0].message, ChatCompletionMessage)}")
    print(f"✓ Usage is a real CompletionUsage: {isinstance(response.usage, CompletionUsage)}")
    print()


if __name__ == "__main__":
    print("Testing Kairix OpenAI-Compatible API with real OpenAI types\n")
    print("Note: This example demonstrates the adapter usage. Server implementation has been moved.\n")
    
    try:
        # Test listing models
        test_list_models()
        
        # Test non-streaming
        test_non_streaming()
        
        # Test streaming
        asyncio.run(test_streaming())
        
        # Test with conversation history
        test_conversation_with_history()
        
        # Test multipart content
        test_multipart_content()
        
        # Demonstrate type safety
        demonstrate_type_safety()
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure the Kairix API server is running on http://localhost:8000")