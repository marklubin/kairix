"""
Gradio Web Application for Dynamic Pipeline Execution

This application automatically discovers pipeline factories and generates
dynamic web interfaces for pipeline configuration and execution with
real-time progress tracking.
"""

from apiana.applications.gradio.app import GradioApp
from apiana.applications.gradio.pipeline_discovery import PipelineDiscovery
from apiana.applications.gradio.ui_components import PipelineUI

__all__ = [
    "GradioApp",
    "PipelineDiscovery", 
    "PipelineUI",
]