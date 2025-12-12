"""Unit tests for batch inference transform component."""

import pytest
from typing import List, Optional
from unittest.mock import Mock

from apiana.core.components.transform.batch_inference import (
    BatchInferenceTransform,
    BatchConfig,
)
from apiana.core.components.common.base import ComponentResult


class MockProvider:
    """Mock provider for testing."""
    
    def __init__(self, process_func=None, fail_count=0):
        self.process_func = process_func
        self.fail_count = fail_count
        self.call_count = 0
        self.calls = []
    
    def process_batch(self, items: List[str]) -> List[str]:
        """Process a batch of items."""
        self.calls.append(items)
        self.call_count += 1
        
        if self.call_count <= self.fail_count:
            raise Exception(f"Mock failure {self.call_count}")
        
        if self.process_func:
            return self.process_func(items)
        
        # Default: uppercase each item
        return [item.upper() for item in items]


class MockStore:
    """Mock store for testing."""
    
    def __init__(self, initial_data=None):
        self.storage = initial_data or {}
        self.get_calls = []
        self.store_calls = []
    
    def get_by_hash(self, hash_key: str) -> Optional[str]:
        """Get item by hash."""
        self.get_calls.append(hash_key)
        return self.storage.get(hash_key)
    
    def store_result(self, hash_key: str, input_item: str, result: str) -> None:
        """Store result."""
        self.store_calls.append((hash_key, input_item, result))
        self.storage[hash_key] = result


def simple_hash(item: str) -> str:
    """Simple hash function for testing."""
    return f"hash_{item}"


class TestBatchInferenceTransform:
    """Test cases for BatchInferenceTransform."""
    
    @pytest.fixture
    def mock_provider(self):
        """Create mock provider."""
        return MockProvider()
    
    @pytest.fixture
    def mock_store(self):
        """Create mock store."""
        return MockStore()
    
    @pytest.fixture
    def config(self):
        """Create default config."""
        return BatchConfig(
            batch_size=3,
            hash_function=simple_hash,
            max_retries=3,
            retry_delay=0.1
        )
    
    @pytest.fixture
    def transform(self, mock_provider, mock_store, config):
        """Create transform instance."""
        return BatchInferenceTransform(
            provider=mock_provider,
            store=mock_store,
            config=config
        )
    
    def test_empty_input(self, transform):
        """Test processing empty input."""
        result = transform.process([])
        assert isinstance(result, ComponentResult)
        assert result.data == []
        assert result.success
    
    def test_single_batch(self, transform):
        """Test processing items that fit in single batch."""
        inputs = ["a", "b", "c"]
        result = transform.process(inputs)
        
        assert isinstance(result, ComponentResult)
        assert result.data == ["A", "B", "C"]
        assert result.success
        assert transform.provider.call_count == 1
        assert transform.provider.calls[0] == inputs
        assert result.metadata["total_items"] == 3
        assert result.metadata["batch_count"] == 1
        assert result.metadata["cached_items"] == 0
        assert result.metadata["processed_items"] == 3
    
    def test_multiple_batches(self, transform):
        """Test processing items that require multiple batches."""
        inputs = ["a", "b", "c", "d", "e", "f", "g"]
        result = transform.process(inputs)
        
        assert isinstance(result, ComponentResult)
        assert result.data == ["A", "B", "C", "D", "E", "F", "G"]
        assert result.success
        assert transform.provider.call_count == 3
        assert transform.provider.calls[0] == ["a", "b", "c"]
        assert transform.provider.calls[1] == ["d", "e", "f"]
        assert transform.provider.calls[2] == ["g"]
        assert result.metadata["total_items"] == 7
        assert result.metadata["batch_count"] == 3
    
    def test_exact_batch_boundaries(self, transform):
        """Test when input size is exact multiple of batch size."""
        inputs = ["a", "b", "c", "d", "e", "f"]
        result = transform.process(inputs)
        
        assert result.data == ["A", "B", "C", "D", "E", "F"]
        assert result.success
        assert transform.provider.call_count == 2
        assert transform.provider.calls[0] == ["a", "b", "c"]
        assert transform.provider.calls[1] == ["d", "e", "f"]
    
    def test_retry_on_failure(self, mock_store, config):
        """Test retry logic on provider failure."""
        # Provider fails once then succeeds
        provider = MockProvider(fail_count=1)
        transform = BatchInferenceTransform(
            provider=provider,
            store=mock_store,
            config=config
        )
        
        inputs = ["a", "b"]
        result = transform.process(inputs)
        
        assert result.data == ["A", "B"]
        assert result.success
        assert provider.call_count == 2  # First attempt failed, second succeeded
    
    def test_max_retries_exceeded(self, mock_store, config):
        """Test when all retries are exhausted."""
        # Provider always fails
        provider = MockProvider(fail_count=10)
        transform = BatchInferenceTransform(
            provider=provider,
            store=mock_store,
            config=config
        )
        
        inputs = ["a", "b"]
        with pytest.raises(RuntimeError) as exc_info:
            transform.process(inputs)
        
        assert "Batch processing failed" in str(exc_info.value)
        assert provider.call_count == 3
    
    def test_provider_wrong_result_count(self, mock_store, config):
        """Test when provider returns wrong number of results."""
        # Provider returns wrong number of results
        provider = MockProvider(process_func=lambda items: ["X"])
        transform = BatchInferenceTransform(
            provider=provider,
            store=mock_store,
            config=config
        )
        
        inputs = ["a", "b"]
        with pytest.raises(RuntimeError) as exc_info:
            transform.process(inputs)
        
        assert "Provider returned 1 results for 2 inputs" in str(exc_info.value)
    
    def test_large_batch_processing(self, transform):
        """Test processing large number of items."""
        inputs = [f"item_{i}" for i in range(100)]
        result = transform.process(inputs)
        
        assert len(result.data) == 100
        assert all(r == i.upper() for i, r in zip(inputs, result.data))
        # With batch size 3, we should have 34 batches (33 full + 1 partial)
        assert transform.provider.call_count == 34
    
    def test_custom_process_function(self, mock_store, config):
        """Test with custom processing function."""
        # Provider that reverses strings
        provider = MockProvider(process_func=lambda items: [item[::-1] for item in items])
        transform = BatchInferenceTransform(
            provider=provider,
            store=mock_store,
            config=config
        )
        
        inputs = ["hello", "world"]
        result = transform.process(inputs)
        
        assert result.data == ["olleh", "dlrow"]
        assert result.success
    
    def test_partial_batch_retry(self, mock_store):
        """Test retry with different batch sizes."""
        config = BatchConfig(
            batch_size=2,
            hash_function=simple_hash,
            max_retries=3,
            retry_delay=0.01
        )
        
        # Fail on first batch only
        call_count = 0
        def failing_process(items):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and len(items) == 2:
                raise Exception("First batch failed")
            return [item.upper() for item in items]
        
        provider = Mock()
        provider.process_batch = failing_process
        
        transform = BatchInferenceTransform(
            provider=provider,
            store=mock_store,
            config=config
        )
        
        inputs = ["a", "b", "c"]
        result = transform.process(inputs)
        
        assert result.data == ["A", "B", "C"]
        assert call_count == 3  # Failed once on first batch, then succeeded
    
    def test_input_output_types(self, transform):
        """Test component type declarations."""
        assert transform.input_types == [list]
        assert transform.output_types == [list]
    
    def test_component_name(self, mock_provider, mock_store, config):
        """Test component naming."""
        # Default name
        transform1 = BatchInferenceTransform(
            provider=mock_provider,
            store=mock_store,
            config=config
        )
        assert transform1.name == "BatchInferenceTransform"
        
        # Custom name
        transform2 = BatchInferenceTransform(
            provider=mock_provider,
            store=mock_store,
            config=config,
            name="CustomBatch"
        )
        assert transform2.name == "CustomBatch"
    
    def test_execution_time_tracking(self, transform):
        """Test that execution time is tracked."""
        inputs = ["a", "b", "c"]
        result = transform.process(inputs)
        
        assert result.execution_time_ms > 0
        assert result.timestamp is not None
    
    # New tests for caching and deduplication
    
    def test_cache_hit_all_items(self, mock_provider, config):
        """Test when all items are found in cache."""
        # Pre-populate store with cached results
        store = MockStore(initial_data={
            "hash_a": "CACHED_A",
            "hash_b": "CACHED_B",
            "hash_c": "CACHED_C"
        })
        
        transform = BatchInferenceTransform(
            provider=mock_provider,
            store=store,
            config=config
        )
        
        inputs = ["a", "b", "c"]
        result = transform.process(inputs)
        
        assert result.data == ["CACHED_A", "CACHED_B", "CACHED_C"]
        assert mock_provider.call_count == 0  # No provider calls needed
        assert len(store.get_calls) == 3  # Cache checked for all items
        assert len(store.store_calls) == 0  # Nothing stored (all cached)
        assert result.metadata["cached_items"] == 3
        assert result.metadata["processed_items"] == 0
        assert result.metadata["cache_hit_rate"] == 100.0
    
    def test_cache_hit_partial(self, mock_provider, config):
        """Test when some items are cached and others need processing."""
        # Pre-populate store with some cached results
        store = MockStore(initial_data={
            "hash_a": "CACHED_A",
            "hash_c": "CACHED_C",
            "hash_e": "CACHED_E"
        })
        
        transform = BatchInferenceTransform(
            provider=mock_provider,
            store=store,
            config=config
        )
        
        inputs = ["a", "b", "c", "d", "e", "f"]
        result = transform.process(inputs)
        
        assert result.data == ["CACHED_A", "B", "CACHED_C", "D", "CACHED_E", "F"]
        assert mock_provider.call_count == 1  # One batch for uncached items
        assert mock_provider.calls[0] == ["b", "d", "f"]  # Only uncached items
        assert len(store.get_calls) == 6  # All items checked
        assert len(store.store_calls) == 3  # Only uncached items stored
        assert result.metadata["cached_items"] == 3
        assert result.metadata["processed_items"] == 3
        assert result.metadata["cache_hit_rate"] == 50.0
    
    def test_deduplication_same_items(self, mock_provider, config):
        """Test deduplication when same items appear multiple times."""
        store = MockStore()
        transform = BatchInferenceTransform(
            provider=mock_provider,
            store=store,
            config=config
        )
        
        # Process same items twice
        inputs1 = ["a", "b", "c"]
        result1 = transform.process(inputs1)
        assert result1.data == ["A", "B", "C"]
        assert mock_provider.call_count == 1
        
        # Process same items again - should use cache
        inputs2 = ["a", "b", "c"]
        result2 = transform.process(inputs2)
        assert result2.data == ["A", "B", "C"]
        assert mock_provider.call_count == 1  # No new provider calls
        assert result2.metadata["cached_items"] == 3
        assert result2.metadata["cache_hit_rate"] == 100.0
    
    def test_store_persistence(self, mock_provider, config):
        """Test that results are persisted to store."""
        store = MockStore()
        transform = BatchInferenceTransform(
            provider=mock_provider,
            store=store,
            config=config
        )
        
        inputs = ["a", "b", "c"]
        transform.process(inputs)
        
        # Check that all results were stored
        assert len(store.store_calls) == 3
        assert store.store_calls[0] == ("hash_a", "a", "A")
        assert store.store_calls[1] == ("hash_b", "b", "B")
        assert store.store_calls[2] == ("hash_c", "c", "C")
        
        # Verify storage contents
        assert store.storage["hash_a"] == "A"
        assert store.storage["hash_b"] == "B"
        assert store.storage["hash_c"] == "C"
    
    def test_mixed_order_with_cache(self, mock_provider, config):
        """Test that results maintain original order even with mixed cache hits."""
        store = MockStore(initial_data={
            "hash_b": "CACHED_B",
            "hash_d": "CACHED_D"
        })
        
        transform = BatchInferenceTransform(
            provider=mock_provider,
            store=store,
            config=config
        )
        
        inputs = ["a", "b", "c", "d", "e"]
        result = transform.process(inputs)
        
        # Results should maintain original order
        assert result.data == ["A", "CACHED_B", "C", "CACHED_D", "E"]
    
    def test_hash_function_called(self, mock_provider, mock_store):
        """Test that hash function is called for each input."""
        hash_calls = []
        
        def tracking_hash(item):
            hash_calls.append(item)
            return f"tracked_hash_{item}"
        
        config = BatchConfig(
            batch_size=3,
            hash_function=tracking_hash,
            max_retries=3,
            retry_delay=0.1
        )
        
        transform = BatchInferenceTransform(
            provider=mock_provider,
            store=mock_store,
            config=config
        )
        
        inputs = ["x", "y", "z"]
        transform.process(inputs)
        
        assert hash_calls == ["x", "y", "z"]
        assert mock_store.get_calls == ["tracked_hash_x", "tracked_hash_y", "tracked_hash_z"]
    
    def test_batch_processing_with_cache_gaps(self, mock_provider, config):
        """Test batch processing when cached items create gaps."""
        # Cache every other item
        store = MockStore(initial_data={
            "hash_a": "CACHED_A",
            "hash_c": "CACHED_C",
            "hash_e": "CACHED_E",
            "hash_g": "CACHED_G"
        })
        
        transform = BatchInferenceTransform(
            provider=mock_provider,
            store=store,
            config=config
        )
        
        inputs = ["a", "b", "c", "d", "e", "f", "g", "h"]
        result = transform.process(inputs)
        
        # Should process uncached items in optimal batches
        assert result.data == ["CACHED_A", "B", "CACHED_C", "D", "CACHED_E", "F", "CACHED_G", "H"]
        assert mock_provider.call_count == 2  # Two batches: ["b", "d", "f"] and ["h"]
        assert mock_provider.calls[0] == ["b", "d", "f"]
        assert mock_provider.calls[1] == ["h"]