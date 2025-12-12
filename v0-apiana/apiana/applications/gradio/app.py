"""
Main Gradio Application

Provides a web interface for discovering, configuring, and executing
pipelines with real-time progress tracking and execution history.
Uses type introspection to automatically generate UI components.
"""

import gradio as gr
from typing import Dict, Any, List, get_type_hints, Union, get_origin, get_args
import threading
import logging
import inspect
from datetime import datetime
from pathlib import Path
import uuid

from apiana.applications.gradio.pipeline_discovery import get_pipeline_discovery
from apiana.applications.gradio.ui_components import PipelineUI
import pipelines


class PipelineExecution:
    """Represents a single pipeline execution with its state and logs."""
    
    def __init__(self, execution_id: str, pipeline_name: str, parameters: Dict[str, Any]):
        self.id = execution_id
        self.pipeline_name = pipeline_name
        self.parameters = parameters
        self.status = "queued"
        self.logs = []
        self.progress = 0
        self.result = None
        self.error = None
        self.started_at = datetime.now()
        self.completed_at = None
        self.thread = None
        
    def add_log(self, message: str):
        """Add a log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.logs.append(f"[{timestamp}] {message}")
        
    def set_progress(self, progress: int):
        """Update progress percentage."""
        self.progress = min(100, max(0, progress))
        
    def complete(self, result: Any = None, error: str = None):
        """Mark execution as complete."""
        self.completed_at = datetime.now()
        if error:
            self.status = "failed"
            self.error = error
            self.add_log(f"❌ Execution failed: {error}")
        else:
            self.status = "completed"
            self.result = result
            self.add_log("✅ Execution completed successfully")
        self.progress = 100


class GradioApp:
    """Main Gradio application for pipeline execution."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7860):
        """
        Initialize the Gradio application.
        
        Args:
            host: Host address to bind to
            port: Port to bind to
        """
        self.host = host
        self.port = port
        self.discovery = get_pipeline_discovery()
        self.ui = PipelineUI()
        self.interface = None
        self.executions: Dict[str, PipelineExecution] = {}
        self.execution_order: List[str] = []  # Track order for display
        
        # Setup logging for the application
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def create_interface(self) -> gr.Blocks:
        """Create the main Gradio interface."""
        
        with gr.Blocks(
            theme=self.ui.create_custom_theme(),
            title="Apiana AI Pipeline Runner",
            css=self._get_custom_css()
        ) as interface:
            
            # Header
            gr.Markdown("""
            # 🚀 Apiana AI Pipeline Runner
            
            Select a pipeline and configure its parameters to execute.
            """)
            
            # Pipeline selection section
            with gr.Group():
                gr.Markdown("### Pipeline Selection")
                
                # Get all available pipelines as a flat list
                pipeline_names = sorted(self.discovery.get_pipeline_names())
                
                selected_pipeline = gr.State(None)
                
                pipeline_dropdown = gr.Dropdown(
                    choices=pipeline_names,
                    label="Select Pipeline",
                    value=None,
                    elem_id="pipeline_selector"
                )
                
                pipeline_description = gr.Markdown(
                    "Select a pipeline to see its description and parameters.",
                    elem_id="pipeline_description"
                )
            
            # Dynamic parameter form section
            @gr.render(inputs=selected_pipeline)
            def render_parameter_form(pipeline_name):
                if not pipeline_name:
                    return
                
                with gr.Group():
                    gr.Markdown("### Pipeline Parameters")
                    
                    # Get function signature and type hints
                    pipeline_func = getattr(pipelines, pipeline_name)
                    sig = inspect.signature(pipeline_func)
                    type_hints = get_type_hints(pipeline_func)
                    
                    # Create inputs for each parameter
                    param_inputs = {}
                    for param_name, param in sig.parameters.items():
                        # Get parameter type from type hints
                        param_type = type_hints.get(param_name, type(param.default) if param.default != inspect.Parameter.empty else str)
                        default = param.default if param.default != inspect.Parameter.empty else None
                        
                        # Create appropriate input based on type
                        param_inputs[param_name] = self._create_input_for_type(
                            param_name, param_type, default
                        )
                    
                    # Execute button
                    execute_btn = gr.Button(
                        "🚀 Execute Pipeline",
                        variant="primary",
                        size="lg",
                        elem_id="execute_button"
                    )
                    
                    # Handle execution
                    def execute_pipeline(*param_values):
                        # Create parameter dictionary
                        parameters = {}
                        param_names = list(param_inputs.keys())
                        
                        for name, value in zip(param_names, param_values):
                            if value is not None:
                                # Handle file inputs
                                if hasattr(value, 'name'):  # It's a file
                                    parameters[name] = Path(value.name)
                                else:
                                    parameters[name] = value
                        
                        # Create execution
                        execution_id = str(uuid.uuid4())[:8]
                        execution = PipelineExecution(execution_id, pipeline_name, parameters)
                        
                        # Add to tracking
                        self.executions[execution_id] = execution
                        self.execution_order.insert(0, execution_id)  # Add to front
                        
                        # Start execution in thread
                        def run_pipeline():
                            try:
                                execution.status = "running"
                                execution.add_log(f"Starting execution of {pipeline_name}")
                                
                                # Get pipeline factory
                                pipeline_func = getattr(pipelines, pipeline_name)
                                
                                # Create pipeline instance
                                execution.add_log("Creating pipeline instance...")
                                pipeline = pipeline_func(**parameters)
                                
                                # Execute pipeline
                                execution.add_log("Executing pipeline...")
                                execution.set_progress(10)
                                
                                # Capture logs from the pipeline
                                class ExecutionLogHandler(logging.Handler):
                                    def emit(self, record):
                                        execution.add_log(record.getMessage())
                                        # Update progress based on log messages
                                        if "iteration" in record.getMessage().lower():
                                            # Extract iteration info if available
                                            msg = record.getMessage()
                                            if "/" in msg:
                                                try:
                                                    parts = msg.split("/")
                                                    for part in parts:
                                                        if part.strip().isdigit():
                                                            current = int(part.strip())
                                                            break
                                                    for part in reversed(parts):
                                                        if part.strip().isdigit():
                                                            total = int(part.strip())
                                                            break
                                                    if 'current' in locals() and 'total' in locals():
                                                        execution.set_progress(10 + int(current / total * 80))
                                                except Exception:
                                                    pass
                                
                                # Add handler temporarily
                                handler = ExecutionLogHandler()
                                handler.setLevel(logging.INFO)
                                logger = logging.getLogger()
                                logger.addHandler(handler)
                                
                                try:
                                    # Determine input data based on pipeline requirements
                                    if "input_file" in parameters:
                                        result = pipeline.run(parameters["input_file"])
                                    else:
                                        result = pipeline.run(None)
                                finally:
                                    logger.removeHandler(handler)
                                
                                execution.complete(result=result)
                                
                            except Exception as e:
                                execution.complete(error=str(e))
                        
                        execution.thread = threading.Thread(target=run_pipeline)
                        execution.thread.start()
                        
                        return f"Started execution {execution_id}"
                    
                    # Connect execute button
                    execute_btn.click(
                        execute_pipeline,
                        inputs=list(param_inputs.values()),
                        outputs=gr.Textbox(visible=False)  # Hidden output
                    )
            
            # Clear history button
            with gr.Row():
                clear_history_btn = gr.Button(
                    "🗑️ Clear History",
                    variant="secondary",
                    elem_id="clear_history"
                )
            
            # Execution history section
            gr.Markdown("### Execution History")
            
            # Execution history display
            execution_history_display = gr.Markdown(
                "*Pipeline executions will appear here with real-time updates*",
                elem_id="execution_history"
            )
            
            # Timer for periodic updates
            timer = gr.Timer(0.5)
            
            def update_execution_history():
                """Update the execution history display."""
                if not self.execution_order:
                    return "*No executions yet*"
                
                # Build markdown content for all executions
                history_md = ""
                
                for exec_id in self.execution_order:
                    if exec_id not in self.executions:
                        continue
                    
                    execution = self.executions[exec_id]
                    
                    # Status emoji
                    status_emoji = {
                        "queued": "⏳",
                        "running": "🔄",
                        "completed": "✅",
                        "failed": "❌"
                    }.get(execution.status, "❓")
                    
                    # Header with pipeline name and status
                    header = f"{status_emoji} **{execution.pipeline_name}** - {execution.status.upper()}"
                    if execution.completed_at:
                        duration = (execution.completed_at - execution.started_at).total_seconds()
                        header += f" ({duration:.1f}s)"
                    
                    history_md += f"\n\n---\n\n{header}\n\n"
                    
                    # Progress if running
                    if execution.status == "running" and execution.progress > 0:
                        history_md += f"**Progress:** {execution.progress}%\n\n"
                    
                    # Show last few logs (for running or recently completed)
                    if execution.logs:
                        if execution.status == "running" or (execution.completed_at and 
                            (datetime.now() - execution.completed_at).total_seconds() < 5):
                            history_md += "**Recent Logs:**\n```\n"
                            history_md += "\n".join(execution.logs[-5:])
                            history_md += "\n```\n\n"
                    
                    # Error display
                    if execution.error:
                        history_md += f"**Error:** {execution.error}\n\n"
                
                return history_md if history_md else "*No executions yet*"
            
            # Connect timer to update function
            timer.tick(
                update_execution_history,
                outputs=[execution_history_display]
            )
            
            # Event handlers
            def on_pipeline_select(pipeline_name):
                """Handle pipeline selection."""
                if not pipeline_name:
                    return (
                        None,
                        "Select a pipeline to see its description and parameters."
                    )
                
                # Get pipeline metadata
                metadata = self.discovery.get_pipeline_metadata(pipeline_name)
                
                # Create description
                description_md = f"""
                ### {metadata.name}
                
                {metadata.description}
                
                **Estimated Time:** {metadata.estimated_time}  
                **Output:** {metadata.output_description}
                """
                
                return pipeline_name, description_md
            
            def clear_history():
                """Clear execution history."""
                self.executions.clear()
                self.execution_order.clear()
                return "*No executions yet*"
            
            # Connect events
            pipeline_dropdown.change(
                on_pipeline_select,
                inputs=[pipeline_dropdown],
                outputs=[selected_pipeline, pipeline_description]
            )
            
            clear_history_btn.click(
                clear_history,
                outputs=[execution_history_display]
            )
        
        return interface
    
    def _create_input_for_type(self, param_name: str, param_type: type, default: Any) -> gr.Component:
        """Create appropriate Gradio input component based on parameter type."""
        label = param_name.replace("_", " ").title()
        
        # Handle Optional types
        origin = get_origin(param_type)
        if origin is Union:
            args = get_args(param_type)
            # Check if it's Optional (Union[X, None])
            if type(None) in args:
                # Get the non-None type
                param_type = next(arg for arg in args if arg is not type(None))
        
        # Handle Path type
        if param_type == Path or (hasattr(param_type, '__name__') and param_type.__name__ == 'Path'):
            if "file" in param_name.lower():
                return gr.File(
                    label=label,
                    elem_id=f"param_{param_name}"
                )
            else:
                return gr.Textbox(
                    label=label,
                    value=str(default) if default else "",
                    elem_id=f"param_{param_name}"
                )
        
        # Handle string type
        elif param_type is str:
            return gr.Textbox(
                label=label,
                value=default or "",
                elem_id=f"param_{param_name}"
            )
        
        # Handle int type
        elif param_type is int:
            return gr.Number(
                label=label,
                value=default if default is not None else 0,
                precision=0,
                elem_id=f"param_{param_name}"
            )
        
        # Handle float type
        elif param_type is float:
            return gr.Number(
                label=label,
                value=default if default is not None else 0.0,
                elem_id=f"param_{param_name}"
            )
        
        # Handle bool type
        elif param_type is bool:
            return gr.Checkbox(
                label=label,
                value=default if default is not None else False,
                elem_id=f"param_{param_name}"
            )
        
        # Handle List types
        elif origin is list or origin is List:
            return gr.Textbox(
                label=f"{label} (comma-separated)",
                value=",".join(default) if default else "",
                elem_id=f"param_{param_name}"
            )
        
        # Default to textbox
        else:
            return gr.Textbox(
                label=f"{label} ({param_type.__name__ if hasattr(param_type, '__name__') else str(param_type)})",
                value=str(default) if default else "",
                elem_id=f"param_{param_name}"
            )
    
    def _get_custom_css(self) -> str:
        """Get custom CSS for styling."""
        return """
        .log-display {
            font-family: 'Courier New', Monaco, Consolas, monospace !important;
            background-color: #1a1a1a !important;
            color: #f0f0f0 !important;
            border: 1px solid #333 !important;
            font-size: 12px !important;
            padding: 10px !important;
        }
        
        .error-text {
            color: #ff4444 !important;
        }
        
        .gradio-container {
            max-width: 1200px !important;
            margin: auto !important;
        }
        
        #execution_history {
            max-height: 600px;
            overflow-y: auto;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background-color: #f9f9f9;
        }
        """
    
    def launch(self, share: bool = False, debug: bool = False):
        """
        Launch the Gradio application.
        
        Args:
            share: Whether to create a public link
            debug: Whether to enable debug mode
        """
        self.interface = self.create_interface()
        
        self.logger.info(f"Starting Gradio application on {self.host}:{self.port}")
        self.logger.info("System dependencies initialized from global system module")
        
        self.interface.launch(
            server_name=self.host,
            server_port=self.port,
            share=share,
            debug=debug,
            show_error=True,
            quiet=not debug
        )
    
    def close(self):
        """Close the Gradio application."""
        if self.interface:
            self.interface.close()
            self.logger.info("Gradio application closed")


def create_app(host: str = "127.0.0.1", port: int = 7860) -> GradioApp:
    """
    Create a new Gradio application instance.
    
    Args:
        host: Host address to bind to
        port: Port to bind to
        
    Returns:
        GradioApp instance
    """
    return GradioApp(host=host, port=port)