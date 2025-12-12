"""Batch inference transform component for efficient LLM API usage."""

import logging
import time
from typing import TypeVar, Generic, Callable, Protocol, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from apiana.core.components.common.base import Component, ComponentResult

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Input type
R = TypeVar('R')  # Result type


class BatchStore(Protocol[T, R]):
    """Storage interface for batch processing results."""
    
    def get_by_hash(self, hash_key: str) -> Optional[R]:
        """Retrieve cached result by hash key."""
        ...
    
    def store_result(self, hash_key: str, input_item: T, result: R) -> None:
        """Store computation result with hash key."""
        ...


class BatchProvider(Protocol[T, R]):
    """Provider interface that supports batch processing."""
    
    def process_batch(self, items: List[T]) -> List[R]:
        """Process a batch of items and return results in order."""
        ...


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    batch_size: int
    hash_function: Callable[[T], str]
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: Optional[float] = None


@dataclass
class ProcessingItem(Generic[T]):
    """Internal wrapper for tracking items during processing."""
    original_index: int
    item: T
    hash_key: str
    cached_result: Optional[Any] = None  # Will hold type R at runtime


class BatchInferenceTransform(Component, Generic[T, R]):
    """
    Generic batch inference transform that:
    1. Accepts collections of inputs
    2. Computes hash keys for deduplication
    3. Checks cache for existing results
    4. Processes only uncached items in batches
    5. Stores results immediately after processing
    6. Returns complete results in original order
    """
    
    def __init__(
        self,
        provider: BatchProvider[T, R],
        store: BatchStore[T, R],
        config: BatchConfig,
        name: Optional[str] = None
    ):
        """Initialize batch inference transform.
        
        Args:
            provider: Provider that supports batch processing
            store: Storage backend for results
            config: Batch processing configuration
            name: Optional component name
        """
        super().__init__(name=name or "BatchInferenceTransform")
        self.provider = provider
        self.store = store
        self.batch_config = config
    
    @property
    def input_types(self) -> List[type]:
        """Return supported input types."""
        return [list]  # List[T]
    
    @property
    def output_types(self) -> List[type]:
        """Return output types."""
        return [list]  # List[R]
    
    def process(self, inputs: List[T]) -> ComponentResult:
        """Process input items in batches with deduplication.
        
        Args:
            inputs: List of items to process
            
        Returns:
            ComponentResult containing list of results in same order as inputs
        """
        start_time = time.time()
        errors = []
        warnings = []
        
        if not inputs:
            return ComponentResult(
                data=[],
                execution_time_ms=0,
                timestamp=datetime.utcnow()
            )
        
        # Step 1: Hash all inputs and create processing items
        processing_items = self._create_processing_items(inputs)
        
        # Step 2: Check cache for existing results
        cached_count = self._check_cache(processing_items)
        
        # Step 3: Filter items that need processing
        items_to_process = [item for item in processing_items if item.cached_result is None]
        
        # Step 4: Process uncached items in batches
        if items_to_process:
            try:
                self._process_uncached_items(items_to_process)
            except Exception as e:
                error_msg = f"Batch processing failed: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                raise
        
        # Step 5: Collect all results in original order
        results = self._collect_results(processing_items)
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return ComponentResult(
            data=results,
            metadata={
                "total_items": len(inputs),
                "cached_items": cached_count,
                "processed_items": len(items_to_process),
                "batch_count": (len(items_to_process) + self.batch_config.batch_size - 1) // self.batch_config.batch_size if items_to_process else 0,
                "batch_size": self.batch_config.batch_size,
                "cache_hit_rate": (cached_count / len(inputs) * 100) if inputs else 0
            },
            errors=errors,
            warnings=warnings,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.utcnow()
        )
    
    def _create_processing_items(self, inputs: List[T]) -> List[ProcessingItem[T]]:
        """Create processing items with hash keys.
        
        Args:
            inputs: Original input items
            
        Returns:
            List of ProcessingItem wrappers
        """
        processing_items = []
        for i, item in enumerate(inputs):
            hash_key = self.batch_config.hash_function(item)
            processing_items.append(ProcessingItem(
                original_index=i,
                item=item,
                hash_key=hash_key
            ))
        
        logger.debug(f"Created {len(processing_items)} processing items with hash keys")
        return processing_items
    
    def _check_cache(self, processing_items: List[ProcessingItem[T]]) -> int:
        """Check cache for existing results.
        
        Args:
            processing_items: Items to check in cache
            
        Returns:
            Number of items found in cache
        """
        cached_count = 0
        
        for item in processing_items:
            cached_result = self.store.get_by_hash(item.hash_key)
            if cached_result is not None:
                item.cached_result = cached_result
                cached_count += 1
                logger.debug(f"Cache hit for hash key: {item.hash_key}")
        
        logger.info(f"Found {cached_count}/{len(processing_items)} items in cache")
        return cached_count
    
    def _process_uncached_items(self, items_to_process: List[ProcessingItem[T]]) -> None:
        """Process items that weren't found in cache.
        
        Args:
            items_to_process: Items without cached results
        """
        # Extract just the items for batch processing
        raw_items = [item.item for item in items_to_process]
        
        # Partition into batches
        batches = self._partition_into_batches(raw_items)
        
        # Process each batch
        processed_count = 0
        for i, batch in enumerate(batches):
            try:
                batch_results = self._process_batch_with_retry(batch)
                
                # Store results immediately
                for j, result in enumerate(batch_results):
                    item_index = processed_count + j
                    processing_item = items_to_process[item_index]
                    processing_item.cached_result = result
                    
                    # Persist to store
                    self.store.store_result(
                        processing_item.hash_key,
                        processing_item.item,
                        result
                    )
                    logger.debug(f"Stored result for hash key: {processing_item.hash_key}")
                
                processed_count += len(batch_results)
                
            except Exception as e:
                error_msg = f"Failed to process batch {i+1}/{len(batches)}: {str(e)}"
                logger.error(error_msg)
                # Re-raise with context
                raise RuntimeError(error_msg) from e
    
    def _collect_results(self, processing_items: List[ProcessingItem[T]]) -> List[R]:
        """Collect all results in original order.
        
        Args:
            processing_items: All processing items with results
            
        Returns:
            Results in original input order
        """
        # Sort by original index to maintain order
        sorted_items = sorted(processing_items, key=lambda x: x.original_index)
        
        results = []
        for item in sorted_items:
            if item.cached_result is None:
                raise RuntimeError(f"No result found for item at index {item.original_index}")
            results.append(item.cached_result)
        
        return results
    
    def _partition_into_batches(self, items: List[T]) -> List[List[T]]:
        """Partition items into batches of configured size.
        
        Args:
            items: Items to partition
            
        Returns:
            List of batches
        """
        batch_size = self.batch_config.batch_size
        batches = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batches.append(batch)
        
        logger.debug(f"Partitioned {len(items)} items into {len(batches)} batches")
        return batches
    
    def _process_batch_with_retry(self, batch: List[T]) -> List[R]:
        """Process a single batch with retry logic.
        
        Args:
            batch: Items to process
            
        Returns:
            Results for the batch
            
        Raises:
            Exception: If all retries are exhausted
        """
        last_error = None
        
        for attempt in range(self.batch_config.max_retries):
            try:
                logger.debug(f"Processing batch of {len(batch)} items (attempt {attempt + 1})")
                results = self.provider.process_batch(batch)
                
                if len(results) != len(batch):
                    raise ValueError(
                        f"Provider returned {len(results)} results for {len(batch)} inputs"
                    )
                
                return results
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Batch processing failed (attempt {attempt + 1}/{self.batch_config.max_retries}): {e}"
                )
                
                if attempt < self.batch_config.max_retries - 1:
                    # Exponential backoff
                    delay = self.batch_config.retry_delay * (2 ** attempt)
                    logger.debug(f"Waiting {delay}s before retry")
                    time.sleep(delay)
        
        # All retries exhausted
        raise RuntimeError(
            f"Batch processing failed after {self.batch_config.max_retries} attempts: {last_error}"
        ) from last_error