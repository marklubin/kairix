import asyncio
import pytest
from unittest.mock import Mock
from concurrent.futures import ThreadPoolExecutor

from agents import Model, ModelResponse, ModelSettings, Usage
from openai.types.responses import ResponseOutputMessage, ResponseOutputText

from kairix_core.inference.pooled_model import PooledModel


class MockModel(Model):
    """Mock model for testing pooled model functionality."""
    
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.call_count = 0
        self.responses = []
        
    def get_response(self, *args, **kwargs) -> ModelResponse:
        """Synchronous get_response for testing."""
        self.call_count += 1
        self.responses.append((args, kwargs))
        
        # Create a simple response
        output_text = ResponseOutputText(
            text=f"Response from model {self.model_id} (call {self.call_count})",
            type="output_text",
            annotations=[]
        )
        output_message = ResponseOutputMessage(
            id=f"msg-{self.model_id}-{self.call_count}",
            role="assistant",
            content=[output_text],
            status="completed",
            type="message"
        )
        
        return ModelResponse(
            output=[output_message],
            usage=Usage(),
            response_id=f"resp-{self.model_id}-{self.call_count}"
        )
    
    
    def stream_response(self, *args, **kwargs):
        raise NotImplementedError("Streaming not supported in mock")


class TestPooledModel:
    
    def test_init_with_model_pool(self):
        """Test initialization with a pool of models."""
        models = [MockModel(f"model-{i}") for i in range(3)]
        pooled_model = PooledModel(models)
        
        # Check that pool size matches
        assert pooled_model._pool.qsize() == 3
        assert isinstance(pooled_model._executor, ThreadPoolExecutor)
    
    def test_checkout_checkin(self):
        """Test model checkout and checkin from pool."""
        models = [MockModel(f"model-{i}") for i in range(2)]
        pooled_model = PooledModel(models)
        
        # Checkout a model
        model1 = pooled_model._checkout()
        assert isinstance(model1, MockModel)
        assert pooled_model._pool.qsize() == 1
        
        # Checkout another model
        model2 = pooled_model._checkout()
        assert isinstance(model2, MockModel)
        assert pooled_model._pool.qsize() == 0
        assert model1.model_id != model2.model_id
        
        # Checkin models
        pooled_model._checkin(model1)
        assert pooled_model._pool.qsize() == 1
        pooled_model._checkin(model2)
        assert pooled_model._pool.qsize() == 2
    
    def test_blocking_get_response(self):
        """Test synchronous get_response through the pool."""
        models = [MockModel(f"model-{i}") for i in range(2)]
        pooled_model = PooledModel(models)
        
        # Make a blocking call
        response = pooled_model._blocking_get_response(
            system_instructions="Test system",
            input="Test input",
            model_settings=ModelSettings()
        )
        
        assert isinstance(response, ModelResponse)
        assert len(response.output) == 1
        assert "Response from model" in response.output[0].content[0].text
        
        # Verify one of the models was used
        total_calls = sum(model.call_count for model in models)
        assert total_calls == 1
    
    @pytest.mark.asyncio
    async def test_async_get_response(self):
        """Test async get_response method."""
        models = [MockModel(f"model-{i}") for i in range(2)]
        pooled_model = PooledModel(models)
        
        # Make an async call
        response = await pooled_model.get_response(
            system_instructions="Test system",
            input="Test input",
            model_settings=ModelSettings()
        )
        
        assert isinstance(response, ModelResponse)
        assert len(response.output) == 1
        assert "Response from model" in response.output[0].content[0].text
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling multiple concurrent requests."""
        models = [MockModel(f"model-{i}") for i in range(3)]
        pooled_model = PooledModel(models)
        
        # Create multiple concurrent requests
        tasks = []
        for i in range(5):
            task = pooled_model.get_response(
                system_instructions=f"System {i}",
                input=f"Input {i}",
                model_settings=ModelSettings()
            )
            tasks.append(task)
        
        # Wait for all to complete
        responses = await asyncio.gather(*tasks)
        
        # Verify all requests completed
        assert len(responses) == 5
        for response in responses:
            assert isinstance(response, ModelResponse)
        
        # Verify models were reused (total calls should equal number of requests)
        total_calls = sum(model.call_count for model in models)
        assert total_calls == 5
    
    @pytest.mark.asyncio
    async def test_pool_blocking_behavior(self):
        """Test that requests block when pool is exhausted."""
        # Use a smaller pool to ensure blocking
        models = [MockModel(f"model-{i}") for i in range(1)]
        pooled_model = PooledModel(models)
        
        # Track when models are called
        call_order = []
        
        def track_call(model_id, *args, **kwargs):
            call_order.append(model_id)
            # Simulate some processing time
            import time
            time.sleep(0.1)
            return ModelResponse(
                output=[ResponseOutputMessage(
                    id=f"msg-{model_id}",
                    role="assistant",
                    content=[ResponseOutputText(text=f"Response {model_id}", type="output_text", annotations=[])],
                    status="completed",
                    type="message"
                )],
                usage=Usage(),
                response_id=f"resp-{model_id}"
            )
        
        # Override the model's get_response to track calls
        models[0].get_response = lambda *args, **kwargs: track_call("model-0", *args, **kwargs)
        
        # Start 3 concurrent requests (more than pool size of 1)
        tasks = []
        for i in range(3):
            task = asyncio.create_task(pooled_model.get_response(
                system_instructions=f"System {i}",
                input=f"Input {i}",
                model_settings=ModelSettings()
            ))
            tasks.append(task)
        
        # Wait for all to complete
        responses = await asyncio.gather(*tasks)
        
        # Verify all requests completed
        assert len(responses) == 3
        
        # Verify that calls were serialized (since pool size is 1)
        assert len(call_order) == 3
        assert all(call == "model-0" for call in call_order)
    
    def test_stream_response_not_implemented(self):
        """Test that stream_response raises NotImplementedError."""
        models = [MockModel(f"model-{i}") for i in range(1)]
        pooled_model = PooledModel(models)
        
        with pytest.raises(NotImplementedError, match="Streaming not supported"):
            pooled_model.stream_response(
                system_instructions="Test",
                input="Test"
            )
    
    def test_pool_with_single_model(self):
        """Test pool behavior with just one model."""
        models = [MockModel("single-model")]
        pooled_model = PooledModel(models)
        
        # Make multiple sequential calls
        responses = []
        for i in range(3):
            response = pooled_model._blocking_get_response(
                system_instructions=f"System {i}",
                input=f"Input {i}",
                model_settings=ModelSettings()
            )
            responses.append(response)
        
        # All responses should be valid
        assert len(responses) == 3
        for response in responses:
            assert isinstance(response, ModelResponse)
        
        # The single model should have been used 3 times
        assert models[0].call_count == 3
    
    @pytest.mark.asyncio
    async def test_error_handling_in_model(self):
        """Test that errors in models are properly propagated."""
        # Create a model that raises an error
        error_model = Mock(spec=Model)
        error_model.get_response = Mock(side_effect=RuntimeError("Model error"))
        
        pooled_model = PooledModel([error_model])
        
        # The error should be propagated
        with pytest.raises(RuntimeError, match="Model error"):
            await pooled_model.get_response(
                system_instructions="Test",
                input="Test",
                model_settings=ModelSettings()
            )
        
        # Model should be returned to pool even after error
        assert pooled_model._pool.qsize() == 1