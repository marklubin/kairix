import pytest
from unittest.mock import Mock, patch

from agents import ModelResponse, ModelSettings, Tool, AgentOutputSchemaBase, Handoff
from llama_cpp import Llama
from openai.types.responses import ResponseOutputMessage, ResponseOutputText

from kairix_core.inference.llama_cpp.model import LlamaCppModel
from ..test_model_utils import create_mock_llama_model


class TestLlamaCppModel:
    
    def test_init_with_llama_instance(self):
        """Test initialization with a Llama instance."""
        mock_llama, _ = create_mock_llama_model()
        model = LlamaCppModel(llama=mock_llama)
        assert model.llama == mock_llama
    
    @pytest.mark.asyncio
    async def test_get_response_basic(self):
        """Test basic text response generation."""
        mock_llama, _ = create_mock_llama_model()
        model = LlamaCppModel(llama=mock_llama)
        
        response = await model.sync_complete(
            system_instructions="You are a helpful assistant",
            input="Hello, how are you?",
            model_settings=ModelSettings()
        )
        
        # Verify response structure
        assert isinstance(response, ModelResponse)
        assert len(response.output) == 1
        assert isinstance(response.output[0], ResponseOutputMessage)
        assert response.output[0].role == "assistant"
        assert len(response.output[0].content) == 1
        assert isinstance(response.output[0].content[0], ResponseOutputText)
        assert "Hello" in response.output[0].content[0].text
        
        # Verify the Llama model was called correctly
        mock_llama.create_chat_completion.assert_called_once()
        call_args = mock_llama.create_chat_completion.call_args
        messages = call_args[0][0]
        
        # Check message structure
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello, how are you?"
    
    @pytest.mark.asyncio
    async def test_get_response_with_model_settings(self):
        """Test response generation with custom model settings."""
        mock_llama, _ = create_mock_llama_model()
        model = LlamaCppModel(llama=mock_llama)
        
        settings = ModelSettings(
            temperature=0.7,
            max_tokens=100,
            presence_penalty=0.5,
            frequency_penalty=0.3
        )
        
        response = await model.sync_complete(
            system_instructions="Be concise",
            input="Test input",
            model_settings=settings
        )
        
        # Verify settings were passed to the model
        call_kwargs = mock_llama.create_chat_completion.call_args[1]
        assert call_kwargs.get("tempature") == 0.7  # Note: There's a typo in the original code
        assert call_kwargs.get("max_tokens") == 100
        assert call_kwargs.get("presence_penalty") == 0.5
        assert call_kwargs.get("frequency_penalty") == 0.3
    
    @pytest.mark.asyncio
    async def test_get_response_with_json_schema(self):
        """Test response generation with JSON output schema."""
        mock_llama, _ = create_mock_llama_model()
        model = LlamaCppModel(llama=mock_llama)
        
        # Mock output schema
        mock_schema = Mock(spec=AgentOutputSchemaBase)
        mock_schema.is_plain_text.return_value = False
        mock_schema.json_schema.return_value = {"type": "object", "properties": {"answer": {"type": "string"}}}
        
        response = await model.sync_complete(
            system_instructions="Return JSON",
            input="What is 2+2?",
            model_settings=ModelSettings(),
            output_schema=mock_schema
        )
        
        # Verify JSON response format was requested
        call_kwargs = mock_llama.create_chat_completion.call_args[1]
        response_format = call_kwargs.get("response_format")
        assert response_format["type"] == "json_object"
        assert "schema" in response_format
    
    @pytest.mark.asyncio
    async def test_get_response_non_string_input_error(self):
        """Test that non-string input raises an error."""
        mock_llama, _ = create_mock_llama_model()
        model = LlamaCppModel(llama=mock_llama)
        
        with pytest.raises(Exception, match="only string inputs are presently supported"):
            await model.sync_complete(
                system_instructions="Test",
                input=["list", "input"],  # Non-string input
                model_settings=ModelSettings()
            )
    
    @pytest.mark.asyncio
    async def test_get_response_no_choices_error(self):
        """Test error handling when model returns no choices."""
        mock_llama = Mock(spec=Llama)
        mock_llama.create_chat_completion.return_value = {"choices": []}
        
        model = LlamaCppModel(llama=mock_llama)
        
        with pytest.raises(Exception, match="illegal response from inference, no choices provided"):
            await model.sync_complete(
                system_instructions="Test",
                input="Test input",
                model_settings=ModelSettings()
            )
    
    @pytest.mark.asyncio
    async def test_get_response_missing_content_error(self):
        """Test error handling when response is missing content."""
        mock_llama = Mock(spec=Llama)
        mock_llama.create_chat_completion.return_value = {
            "choices": [{
                "message": {
                    "role": "assistant"
                    # Missing 'content' field
                }
            }]
        }
        
        model = LlamaCppModel(llama=mock_llama)
        
        with pytest.raises(Exception, match="Response was missisng content"):  # Note: typo in original
            await model.sync_complete(
                system_instructions="Test",
                input="Test input",
                model_settings=ModelSettings()
            )
    
    @pytest.mark.asyncio
    async def test_get_response_with_tools_and_handoffs(self):
        """Test that tools and handoffs are passed but currently ignored."""
        mock_llama, _ = create_mock_llama_model()
        model = LlamaCppModel(llama=mock_llama)
        
        # These are currently ignored in the implementation
        mock_tool = Mock(spec=Tool)
        mock_handoff = Mock(spec=Handoff)
        
        response = await model.sync_complete(
            system_instructions="Test",
            input="Test input",
            model_settings=ModelSettings(),
            tools=[mock_tool],
            handoffs=[mock_handoff]
        )
        
        assert isinstance(response, ModelResponse)
        # Tools and handoffs are not passed to llama.create_chat_completion
        call_args = mock_llama.create_chat_completion.call_args
        assert call_args[0][1] is None  # tools parameter
    
    def test_stream_response_not_implemented(self):
        """Test that stream_response raises NotImplementedError."""
        mock_llama, _ = create_mock_llama_model()
        model = LlamaCppModel(llama=mock_llama)
        
        with pytest.raises(NotImplementedError, match="Streaming not yet supported with llama.cpp"):
            # We need to call it as a generator
            gen = model.stream_response(
                system_instructions="Test",
                input="Test",
                model_settings=ModelSettings(),
                tools=[],
                output_schema=None,
                handoffs=[],
                tracing=None,
                previous_response_id=None,
                prompt=None
            )
    
    @pytest.mark.asyncio
    async def test_get_response_with_real_inference(self):
        """Test with actual model inference using a mock that simulates real behavior."""
        # This test uses our mock that provides deterministic responses
        mock_llama, _ = create_mock_llama_model()
        model = LlamaCppModel(llama=mock_llama)
        
        # Test different inputs to verify the mock's behavior
        test_cases = [
            ("Hello world", "Hello! How can I help you today?"),
            ("Run a test", "This is a test response from the mock model."),
            ("Random input", "I received your message: Random input...")
        ]
        
        for input_text, expected_substring in test_cases:
            response = await model.sync_complete(
                system_instructions="You are a helpful assistant",
                input=input_text,
                model_settings=ModelSettings(temperature=0.0)  # Deterministic
            )
            
            assert isinstance(response, ModelResponse)
            assert len(response.output) == 1
            assert expected_substring in response.output[0].content[0].text
    
    @pytest.mark.asyncio
    async def test_response_id_format(self):
        """Test that response IDs follow the expected format."""
        mock_llama, _ = create_mock_llama_model()
        model = LlamaCppModel(llama=mock_llama)
        
        with patch('uuid.uuid4', return_value='test-uuid-1234'):
            response = await model.sync_complete(
                system_instructions="Test",
                input="Test input",
                model_settings=ModelSettings()
            )
        
        # Check the message ID format
        assert response.output[0].id.startswith("llama::")
        assert "test-uuid-1234" in response.output[0].id
    
    @pytest.mark.asyncio 
    async def test_plain_text_output_schema(self):
        """Test response generation with plain text output schema."""
        mock_llama, _ = create_mock_llama_model()
        model = LlamaCppModel(llama=mock_llama)
        
        # Mock output schema that is plain text
        mock_schema = Mock(spec=AgentOutputSchemaBase)
        mock_schema.is_plain_text.return_value = True
        
        response = await model.sync_complete(
            system_instructions="Return plain text",
            input="What is 2+2?",
            model_settings=ModelSettings(),
            output_schema=mock_schema
        )
        
        # Verify text response format was requested (not JSON)
        call_kwargs = mock_llama.create_chat_completion.call_args[1]
        response_format = call_kwargs.get("response_format")
        assert response_format["type"] == "text"
