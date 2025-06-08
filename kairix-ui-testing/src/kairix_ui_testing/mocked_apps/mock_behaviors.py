"""Configurable mock behaviors for testing."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
import time
import json
from pathlib import Path


@dataclass
class MockConfig:
    """Configuration for mock behaviors."""
    # Import behaviors
    import_delay: float = 2.0
    import_should_fail: bool = False
    import_failure_message: str = "Import failed: Mock error"
    import_success_pattern: str = "Successfully imported {count} conversations"
    
    # Summarization behaviors
    summarize_delay: float = 5.0
    summarize_should_fail: bool = False
    summarize_failure_message: str = "Summarization failed: Mock error"
    summarize_progress_steps: int = 10
    summarize_should_timeout: bool = False
    
    # Data behaviors
    mock_conversation_count: int = 42
    mock_message_count: int = 1337
    mock_memory_shard_count: int = 256
    
    # Special behaviors
    random_failures: bool = False
    failure_rate: float = 0.1
    
    # Custom behavior injection
    custom_behaviors: Dict[str, Callable] = field(default_factory=dict)


class MockBehavior:
    """Handles mock behaviors for testing."""
    
    def __init__(self, config: MockConfig):
        self.config = config
        
    def mock_import(self, file_obj, state: Dict):
        """Mock the import functionality with streaming output."""
        
        # Check for no file selected
        if not file_obj:
            yield "No file selected", state
            return
            
        file_name = Path(file_obj.name).name
        
        # Stream: Loading file
        yield f"Loading {file_name}", state
        time.sleep(0.5)
        
        # Check for configured failure during loading
        if self.config.import_should_fail:
            state["import_status"] = "failed"
            yield self.config.import_failure_message, state
            return
        
        # Stream: Loaded conversations
        yield f"Loaded {self.config.mock_conversation_count} conversations.", state
        time.sleep(0.3)
        
        # Process each conversation with streaming
        processed = 0
        skipped = 0
        for i in range(self.config.mock_conversation_count):
            if i % 5 == 0 and self.config.random_failures:  # Some conversations fail randomly
                yield f"Skipping conversation with no title.", state
                skipped += 1
                time.sleep(0.1)
                continue
                
            yield f"Processing conversation: Test Conversation {i+1}", state
            time.sleep(0.1)
            
            # Show message count
            msg_count = 10 + (i * 3)  # Variable message counts
            yield f"# of mappings: {msg_count}", state
            time.sleep(0.1)
            
            # Writing to DB
            yield f"Writing graph db record for Test Conversation {i+1}, # of messages: {msg_count}", state
            time.sleep(self.config.import_delay / self.config.mock_conversation_count)
            processed += 1
        
        # Final summary
        state["import_status"] = "success"
        state["imported_file"] = file_name
        state["conversation_count"] = processed
        
        doc_list = [f"Test Conversation {i+1}" for i in range(processed)]
        final_output = f"finished! Wrote Source Documents:\n" + "\n".join(doc_list)
        yield final_output, state
    
    def mock_summarize(self, agent_name: str, run_id: str, state: Dict):
        """Mock the summarization functionality - returns full output at once (no streaming)."""
        
        # Store agent_name and run_id in state
        state["agent_name"] = agent_name
        state["run_id"] = run_id
        
        # Check if data was imported
        if state.get("import_status") != "success":
            return "❌ No data imported. Please import ChatGPT export first.", state
            
        # Simulate processing with delay
        time.sleep(self.config.summarize_delay)
        
        # Check for timeout
        if self.config.summarize_should_timeout:
            state["summarize_status"] = "timeout"
            return "❌ Process timeout during summarization", state
        
        # Check for configured failure
        if self.config.summarize_should_fail:
            state["summarize_status"] = "failed"
            return self.config.summarize_failure_message, state
            
        # Build output similar to actual function
        output_lines = []
        
        # Simulate processing chunks
        chunk_count = state.get("conversation_count", self.config.mock_conversation_count) * 3
        output_lines.append(f"Split input into {chunk_count} chunks.")
        
        # Simulate existing shards check
        existing_shards = 5 if self.config.random_failures else 0
        if existing_shards > 0:
            output_lines.append(f"Found {existing_shards} existing memory shards.")
        
        # Process new shards
        new_shards = chunk_count - existing_shards
        output_lines.append(f"Processing {new_shards} new chunks...")
        
        # Show some processing details
        for i in range(min(5, new_shards)):  # Show first 5 for brevity
            output_lines.append(f"  - Chunk {i+1}: Generated summary and embedding")
        
        if new_shards > 5:
            output_lines.append(f"  ... and {new_shards - 5} more chunks")
        
        # Final summary
        output_lines.extend([
            "",
            f"✅ Memory synthesis complete!",
            f"Total memory shards: {self.config.mock_memory_shard_count}",
            f"New shards created: {new_shards}",
            f"Embeddings generated: {new_shards}",
            f"Agent: {state.get('agent_name', 'Unknown')}",
            f"Run ID: {state.get('run_id', 'Unknown')}"
        ])
        
        state["summarize_status"] = "success"
        state["memory_shards"] = self.config.mock_memory_shard_count
        
        return "\n".join(output_lines), state