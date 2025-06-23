import pytest
from unittest.mock import patch


from kairix_core.inference.llama_cpp.provider import LlamaCppProvider
from kairix_core.inference.llama_cpp.model import LlamaCppModel
from kairix_core.inference.pooled_model import PooledModel
from ..test_model_utils import create_mock_llama_model


class TestLlamaCppProvider:
    
    @patch('kairix_core.inference.llama_cpp.provider.Llama.from_pretrained')
    def test_init_single_model_pool(self, mock_from_pretrained):
        """Test initialization with a single model and pool size."""
        # Setup mock
        mock_llama, _ = create_mock_llama_model()
        mock_from_pretrained.return_value = mock_llama
        
        # Create provider with one model
        provider = LlamaCppProvider(("nh2-mistral", 3))
        
        # Verify model was created with correct pool size
        assert "nh2-mistral" in provider.models
        assert isinstance(provider.models["nh2-mistral"], PooledModel)
        
        # Verify from_pretrained was called 3 times (pool size)
        assert mock_from_pretrained.call_count == 3
        
        # Verify correct model definition was used
        mock_from_pretrained.assert_called_with(
            repo_id="NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF",
            filename="Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf"
        )
    
    @patch('kairix_core.inference.llama_cpp.provider.Llama.from_pretrained')
    def test_init_multiple_model_pools(self, mock_from_pretrained):
        """Test initialization with multiple models and different pool sizes."""
        # Setup mock
        mock_llama, _ = create_mock_llama_model()
        mock_from_pretrained.return_value = mock_llama
        
        # Create provider with multiple models
        provider = LlamaCppProvider(
            ("nh2-mistral", 2),
            ("nh2-mistral", 4)  # Same model, different pool
        )
        
        # The second definition should overwrite the first
        assert "nh2-mistral" in provider.models
        assert isinstance(provider.models["nh2-mistral"], PooledModel)
        
        # Total calls should be 2 + 4 = 6
        assert mock_from_pretrained.call_count == 6
    
    def test_init_invalid_model_name(self):
        """Test initialization with an invalid model name."""
        with pytest.raises(ValueError, match="No model definition for invalid-model"):
            LlamaCppProvider(("invalid-model", 1))
    
    @patch('kairix_core.inference.llama_cpp.provider.Llama.from_pretrained')
    def test_get_model_existing(self, mock_from_pretrained):
        """Test getting an existing model from the provider."""
        # Setup mock
        mock_llama, _ = create_mock_llama_model()
        mock_from_pretrained.return_value = mock_llama
        
        provider = LlamaCppProvider(("nh2-mistral", 2))
        
        # Get the model
        model = provider.get_model("nh2-mistral")
        
        assert isinstance(model, PooledModel)
        assert model == provider.models["nh2-mistral"]
    
    @patch('kairix_core.inference.llama_cpp.provider.Llama.from_pretrained')
    def test_get_model_non_existing(self, mock_from_pretrained):
        """Test getting a non-existing model raises error."""
        # Setup mock
        mock_llama, _ = create_mock_llama_model()
        mock_from_pretrained.return_value = mock_llama
        
        provider = LlamaCppProvider(("nh2-mistral", 2))
        
        # Try to get a non-configured model
        with pytest.raises(ValueError, match="No configured model pool for other-model"):
            provider.get_model("other-model")
    
    @patch('kairix_core.inference.llama_cpp.provider.Llama.from_pretrained')
    def test_pool_contains_correct_models(self, mock_from_pretrained):
        """Test that the pool contains the correct number of LlamaCppModel instances."""
        # Create distinct mock Llama instances
        mock_llamas = []
        for i in range(3):
            mock_llama, _ = create_mock_llama_model()
            mock_llama.model_id = f"llama-{i}"  # Add identifier for testing
            mock_llamas.append(mock_llama)
        
        mock_from_pretrained.side_effect = mock_llamas
        
        provider = LlamaCppProvider(("nh2-mistral", 3))
        pooled_model = provider.models["nh2-mistral"]
        
        # Extract models from the pool to verify
        models = []
        for _ in range(3):
            model = pooled_model._checkout()
            models.append(model)
        
        # Verify all are LlamaCppModel instances
        for model in models:
            assert isinstance(model, LlamaCppModel)
        
        # Return models to pool
        for model in models:
            pooled_model._checkin(model)
        
        # Verify pool is full again
        assert pooled_model._pool.qsize() == 3
    
    @patch('kairix_core.inference.llama_cpp.provider.Llama.from_pretrained')
    @pytest.mark.asyncio
    async def test_end_to_end_inference(self, mock_from_pretrained):
        """Test end-to-end inference through the provider."""
        # Setup mock
        mock_llama, _ = create_mock_llama_model()
        mock_from_pretrained.return_value = mock_llama
        
        # Create provider
        provider = LlamaCppProvider(("nh2-mistral", 2))
        
        # Get model and make inference
        model = provider.get_model("nh2-mistral")
        from agents import ModelSettings
        response = await model.get_response(
            system_instructions="You are helpful",
            input="Hello there",
            model_settings=ModelSettings()
        )
        
        # Verify response
        assert response is not None
        assert len(response.output) == 1
        assert "Hello" in response.output[0].content[0].text
    
    @patch('kairix_core.inference.llama_cpp.provider.Llama.from_pretrained')
    def test_empty_initialization(self, mock_from_pretrained):
        """Test initialization with no models."""
        provider = LlamaCppProvider()
        
        assert provider.models == {}
        assert mock_from_pretrained.call_count == 0
    
    @patch('kairix_core.inference.llama_cpp.provider.Llama.from_pretrained')
    def test_model_definition_structure(self, mock_from_pretrained):
        """Test that model definitions are used correctly."""
        # Track how from_pretrained is called
        call_kwargs_list = []
        
        def track_calls(**kwargs):
            call_kwargs_list.append(kwargs)
            mock_llama, _ = create_mock_llama_model()
            return mock_llama
        
        mock_from_pretrained.side_effect = track_calls
        
        # Create provider
        LlamaCppProvider(("nh2-mistral", 1))
        
        # Verify the model definition was passed correctly
        assert len(call_kwargs_list) == 1
        assert call_kwargs_list[0]["repo_id"] == "NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF"
        assert call_kwargs_list[0]["filename"] == "Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf"
    
    @patch('kairix_core.inference.llama_cpp.provider._model_definitions', {
        "test-model": {
            "repo_id": "test/repo",
            "filename": "test.gguf"
        },
        "another-model": {
            "repo_id": "another/repo", 
            "filename": "another.gguf"
        }
    })
    @patch('kairix_core.inference.llama_cpp.provider.Llama.from_pretrained')
    def test_custom_model_definitions(self, mock_from_pretrained):
        """Test with custom model definitions."""
        mock_llama, _ = create_mock_llama_model()
        mock_from_pretrained.return_value = mock_llama
        
        # Create provider with custom models
        provider = LlamaCppProvider(
            ("test-model", 1),
            ("another-model", 2)
        )
        
        # Verify both models were created
        assert "test-model" in provider.models
        assert "another-model" in provider.models
        
        # Verify correct number of model instances
        assert mock_from_pretrained.call_count == 3  # 1 + 2