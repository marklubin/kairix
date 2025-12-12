"""
Manager components for orchestrating pipeline execution and metadata tracking.

These components provide high-level pipeline management capabilities including
execution tracking, error handling, and metadata collection.
"""

from apiana.core.components.managers.pipeline_run_manager import PipelineRunManager

__all__ = [
    'PipelineRunManager',
]