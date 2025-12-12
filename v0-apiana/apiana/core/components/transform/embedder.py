"""
Embedding processor component for generating embeddings.
"""

import time
from typing import List

from apiana.core.components.common import ComponentResult
from apiana.core.components.transform.base import Transform


class EmbeddingTransform(Transform):
    """Processor that generates embeddings for conversation summaries."""
    
    # Type specifications
    input_types = [List[dict]]  # List of dictionaries with summary data
    output_types = [List[dict]]  # List of dictionaries with summary and embedding data

    def __init__(self, name: str = "embedder", config: dict = None):
        super().__init__(name, config)
        self.embedding_provider = None  # Will be injected

    def set_embedding_provider(self, provider):
        """Inject the embedding provider to use."""
        self.embedding_provider = provider

    def validate_input(self, input_data) -> List[str]:
        """Validate that input is a list of summaries."""
        errors = []

        if self.embedding_provider is None:
            errors.append(
                "Embedding provider not set. Call set_embedding_provider() first."
            )

        if not isinstance(input_data, list):
            errors.append("Input must be a list of summary dictionaries")
            return errors

        for i, item in enumerate(input_data):
            if not isinstance(item, dict):
                errors.append(f"Item {i} must be a dictionary")
            elif "summary" not in item or item["summary"] is None:
                errors.append(f"Item {i} missing valid summary")

        return errors

    def transform(self, data: List[dict]) -> ComponentResult:
        """Transform summaries by generating embeddings."""
        start_time = time.time()

        embeddings = []
        errors = []

        for i, summary_item in enumerate(data):
            try:
                summary_text = summary_item["summary"]
                if summary_text is None:
                    # Skip items without summaries (failed summarization)
                    continue

                # Generate embedding
                vector = self.embedding_provider.embed_query(summary_text)

                embeddings.append(
                    {
                        **summary_item,  # Include all original data
                        "embedding": vector,
                        "embedding_dim": len(vector) if vector else 0,
                    }
                )

            except Exception as e:
                error_msg = f"Failed to generate embedding for item {i}: {e}"
                errors.append(error_msg)
                embeddings.append(
                    {**summary_item, "embedding": None, "error": error_msg}
                )

        execution_time = (time.time() - start_time) * 1000

        metadata = {
            "items_processed": len(data),
            "embeddings_generated": len([e for e in embeddings if e.get("embedding")]),
            "failures": len([e for e in embeddings if e.get("error")]),
        }

        return ComponentResult(
            data=embeddings,
            metadata=metadata,
            errors=errors,
            execution_time_ms=execution_time,
        )
