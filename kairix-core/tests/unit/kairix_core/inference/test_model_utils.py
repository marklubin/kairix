from unittest.mock import Mock, MagicMock
from llama_cpp import Llama


def create_mock_llama_model():
    """Create a mock Llama model that simulates basic behavior without requiring a real GGUF file."""
    mock_llama = Mock(spec=Llama)
    
    # Mock the create_chat_completion method
    def mock_create_chat_completion(messages, *args, **kwargs):
        # Extract user message
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        # Create a simple response based on input
        if "hello" in user_message.lower():
            response_text = "Hello! How can I help you today?"
        elif "test" in user_message.lower():
            response_text = "This is a test response from the mock model."
        else:
            response_text = f"I received your message: {user_message[:50]}..."
        
        return {
            "id": "mock-completion-id",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "mock-model",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
    
    mock_llama.create_chat_completion = MagicMock(side_effect=mock_create_chat_completion)
    
    # Mock the from_pretrained method to return our mock
    mock_from_pretrained = MagicMock(return_value=mock_llama)
    
    return mock_llama, mock_from_pretrained


def create_tiny_test_model():
    """Create a super tiny test model configuration for quick testing."""
    # For actual inference tests, we'll use a very small publicly available model
    # or mock the Llama object to avoid downloading large files during tests
    return {
        "repo_id": "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
        "filename": "tinyllama-1.1b-chat-v1.0.Q2_K.gguf",  # Smallest quantization
        "model_kwargs": {
            "n_ctx": 512,  # Small context window
            "n_threads": 1,  # Single thread for consistency
            "n_gpu_layers": 0,  # CPU only for tests
            "seed": 42,  # Fixed seed for reproducibility
            "verbose": False
        }
    }