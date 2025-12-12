"""
Writer components for persisting specific entity types during pipeline execution.

These components provide transparent data persistence, allowing pipelines to
capture and store data while passing it through for continued processing.
"""

from apiana.core.components.writers.base import Writer
from apiana.core.components.writers.chat_fragment_writer import ChatFragmentWriter
from apiana.core.components.writers.pipeline_run_writer import PipelineRunWriter
from apiana.core.components.writers.memory_block_writer import MemoryBlockWriter

__all__ = [
    'Writer',
    'ChatFragmentWriter',
    'PipelineRunWriter', 
    'MemoryBlockWriter',
]