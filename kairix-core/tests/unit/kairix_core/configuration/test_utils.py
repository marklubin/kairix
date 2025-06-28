"""
Test scenarios for configuration.utils module:

1. Test model_for_provider function:
   - Test OpenAI provider returns model name unchanged
   - Test ollama-remote provider returns "ollama-remote/model"
   - Test ollama-local provider returns "ollama-local/model"
   - Test llama-cpp provider returns "llama-cpp/model"
   - Test with empty model name
   - Test with special characters in model name
   - Test all ProviderName literal values are handled
"""