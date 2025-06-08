"""Mock patches for the real memory pipeline dependencies."""

import time
from typing import Generator, Dict, Any, Optional
from unittest.mock import MagicMock
from pathlib import Path


class MockPatches:
    """Provides mock implementations for patching real dependencies."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.imported_data = []
        
    def mock_initialize_processing(self):
        """Mock initialization - instant success."""
        time.sleep(0.1)  # Simulate minimal startup
        
    def mock_load_sources_from_gpt_export(self, file_name: str | list[str]) -> Generator[str, None, None]:
        """Mock implementation with streaming output."""
        # Check for no file selected scenario
        if self.config.get("no_file_selected"):
            yield "No file selected"
            return
            
        if isinstance(file_name, list):
            if not file_name:
                yield "No file selected"
                return
            file_name = file_name[0]
            
        # Check for configured behaviors
        if self.config.get("import_should_fail"):
            yield f"Loading {file_name}"
            time.sleep(0.5)
            yield self.config.get("import_failure_message", "Import failed: Mock error")
            return
            
        # Normal flow
        yield f"Loading {file_name}"
        time.sleep(0.3)
        
        conv_count = self.config.get("mock_conversation_count", 5)
        yield f"Loaded {conv_count} conversations."
        time.sleep(0.2)
        
        # Stream processing of conversations
        documents = []
        for i in range(conv_count):
            # Simulate some conversations being skipped
            if i % 4 == 0 and self.config.get("random_failures"):
                yield "Skipping conversation with no title."
                time.sleep(0.05)
                continue
                
            title = f"Test Conversation {i+1}"
            yield f"Processing conversation: {title}"
            time.sleep(0.05)
            
            msg_count = 10 + (i * 3)
            yield f"# of mappings: {msg_count}"
            time.sleep(0.05)
            
            yield f"Writing graph db record for {title}, # of messages: {msg_count}"
            time.sleep(0.1)
            
            documents.append(title)
            
        # Store for later synthesis
        self.imported_data = documents
        
        # Final message
        yield "finished! Wrote Source Documents:\n" + "\n".join(documents)
        
    def mock_synth_memories(self, agent_name: str, run_id: str) -> str:
        """Mock memory synthesis - returns full output at once."""
        # Check for validation scenario
        if self.config.get("synthesis_validate_inputs"):
            if not agent_name or not run_id:
                return "Please provide agent name and run ID"
                
        # Check for no data scenario
        if self.config.get("synthesis_no_data") or not self.imported_data:
            return "❌ No data imported. Please import ChatGPT export first."
            
        # Simulate processing delay
        delay = self.config.get("summarize_delay", 2.0)
        time.sleep(delay)
        
        # Check for configured failures
        if self.config.get("summarize_should_timeout"):
            return "❌ Process timeout during summarization"
            
        if self.config.get("summarize_should_fail"):
            return self.config.get("summarize_failure_message", "Summarization failed: Mock error")
            
        # Build realistic output
        chunk_count = len(self.imported_data) * 3
        shard_count = self.config.get("mock_memory_shard_count", chunk_count * 2)
        
        output_lines = [
            f"Split input into {chunk_count} chunks.",
            f"Processing {chunk_count} chunks...",
            "",
            "✅ Memory Synthesis Complete",
            f"Agent: {agent_name}",
            f"Run ID: {run_id}",
            f"Total memory shards: {shard_count}",
            f"New shards created: {chunk_count}",
            f"Embeddings generated: {chunk_count}",
            "",
            "Memories created:",
        ]
        
        # Add references to imported conversations
        for doc in self.imported_data[:3]:  # Show first 3
            output_lines.append(f"  - {doc}")
        if len(self.imported_data) > 3:
            output_lines.append(f"  ... and {len(self.imported_data) - 3} more")
        
        return "\n".join(output_lines)


def create_mock_patches(config: Optional[Dict[str, Any]] = None) -> MockPatches:
    """Create a MockPatches instance for the memory pipeline."""
    return MockPatches(config)