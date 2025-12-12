"""
Dynamic UI Components for Pipeline Execution

Creates dynamic Gradio components based on discovered pipeline metadata
with custom styling and real-time progress tracking.
"""

import gradio as gr
from typing import Dict, Any, List, Callable
import threading
import logging
import io

from apiana.applications.gradio.pipeline_discovery import get_pipeline_discovery


class LogCapture:
    """Captures log output for real-time display in the UI."""
    
    def __init__(self):
        self.log_buffer = io.StringIO()
        self.handler = logging.StreamHandler(self.log_buffer)
        self.handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
        )
        self.handler.setFormatter(formatter)
        
        # Add handler to root logger
        logging.getLogger().addHandler(self.handler)
        logging.getLogger().setLevel(logging.INFO)
    
    def get_logs(self) -> str:
        """Get current log content."""
        return self.log_buffer.getvalue()
    
    def clear_logs(self):
        """Clear the log buffer."""
        self.log_buffer.seek(0)
        self.log_buffer.truncate(0)


class PipelineExecutor:
    """Handles pipeline execution in separate threads with progress tracking."""
    
    def __init__(self):
        self.current_execution = None
        self.execution_status = "idle"
        self.execution_logs = LogCapture()
        
    def execute_pipeline(
        self, 
        pipeline_name: str, 
        inputs: Dict[str, Any],
        progress_callback: Callable[[str, int, int], None] = None,
        log_callback: Callable[[str], None] = None
    ):
        """
        Execute a pipeline in a separate thread.
        
        Args:
            pipeline_name: Name of the pipeline to execute
            inputs: Input parameters for the pipeline
            progress_callback: Callback for progress updates (stage, current, total)
            log_callback: Callback for log updates
        """
        if self.current_execution and self.current_execution.is_alive():
            raise RuntimeError("A pipeline is already executing")
        
        self.execution_status = "starting"
        self.execution_logs.clear_logs()
        
        def run_pipeline():
            try:
                discovery = get_pipeline_discovery()
                
                # Update status
                self.execution_status = "running"
                if progress_callback:
                    progress_callback("Initializing Pipeline", 0, 100)
                
                # Create pipeline instance
                pipeline = discovery.create_pipeline_instance(pipeline_name, inputs)
                
                if progress_callback:
                    progress_callback("Pipeline Created", 10, 100)
                
                # Get input data based on pipeline type
                input_data = self._prepare_input_data(inputs)
                
                if progress_callback:
                    progress_callback("Executing Pipeline", 20, 100)
                
                # Execute pipeline
                result = pipeline.run(input_data)
                
                if progress_callback:
                    progress_callback("Pipeline Completed", 100, 100)
                
                self.execution_status = "completed"
                self.execution_result = result
                
            except Exception as e:
                self.execution_status = "failed"
                self.execution_error = str(e)
                logging.error(f"Pipeline execution failed: {e}")
                if progress_callback:
                    progress_callback("Pipeline Failed", 100, 100)
        
        self.current_execution = threading.Thread(target=run_pipeline)
        self.current_execution.start()
    
    def _prepare_input_data(self, inputs: Dict[str, Any]) -> Any:
        """Prepare input data for pipeline execution."""
        # For file-based pipelines, return the file path
        if "input_file" in inputs:
            return str(inputs["input_file"])
        else:
            # For other pipelines, may need different logic
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current execution status."""
        status = {
            "status": self.execution_status,
            "logs": self.execution_logs.get_logs()
        }
        
        if hasattr(self, "execution_result"):
            status["result"] = self.execution_result
        if hasattr(self, "execution_error"):
            status["error"] = self.execution_error
            
        return status


class PipelineUI:
    """Creates dynamic UI components for pipeline configuration and execution."""
    
    def __init__(self):
        self.discovery = get_pipeline_discovery()
        self.executor = PipelineExecutor()
        self.current_pipeline = None
        
    def create_custom_theme(self) -> gr.Theme:
        """Create custom theme with specified colors."""
        theme = gr.themes.Monochrome()
        
        try:
            return theme.set(
                # Light purple background
                background_fill_primary="#F5F3FF",
                background_fill_secondary="#EDE9FE", 
                
                # Dark bold green for primary text
                body_text_color="#064E3B",
                body_text_color_subdued="#065F46",
                
                # Muted yellow/paper color for code and logs
                code_background_fill="#FFFBEB",
                block_background_fill="#FFFBEB",
                
                # Button colors
                button_primary_background_fill="#064E3B",
                button_primary_text_color="#FFFFFF",
                
                # Input colors
                input_background_fill="#FFFFFF",
                input_border_color="#C4B5FD",
                
                # Progress bar
                stat_background_fill="#10B981"
            )
        except TypeError:
            # Fallback for older Gradio versions or if certain parameters aren't supported
            return theme
    
    def create_neo4j_config_inputs(self) -> List[gr.Component]:
        """Create Neo4j configuration input components."""
        return [
            gr.Textbox(label="Neo4j Username", value="neo4j", key="neo4j_username"),
            gr.Textbox(label="Neo4j Password", type="password", key="neo4j_password"),
            gr.Textbox(label="Neo4j Host", value="localhost", key="neo4j_host"),
            gr.Number(label="Neo4j Port", value=7687, key="neo4j_port"),
            gr.Textbox(label="Neo4j Database", value="neo4j", key="neo4j_database")
        ]
    
    def create_parameter_input(self, param_name: str, param_info: Dict[str, Any]) -> gr.Component:
        """Create an input component for a pipeline parameter."""
        ui_type = param_info["ui_type"]
        label = param_name.replace("_", " ").title()
        description = param_info.get("description", "")
        default_value = param_info.get("default")
        required = param_info.get("required", False)
        
        if description:
            label = f"{label} ({description})"
        if required:
            label = f"* {label}"
        
        if ui_type == "string":
            return gr.Textbox(
                label=label,
                value=default_value or "",
                key=param_name
            )
        elif ui_type == "integer":
            return gr.Number(
                label=label,
                value=default_value or 0,
                precision=0,
                key=param_name
            )
        elif ui_type == "number":
            return gr.Number(
                label=label,
                value=default_value or 0.0,
                key=param_name
            )
        elif ui_type == "boolean":
            return gr.Checkbox(
                label=label,
                value=default_value or False,
                key=param_name
            )
        elif ui_type == "file":
            accept = param_info.get("accept", None)
            return gr.File(
                label=label,
                file_types=[accept] if accept else None,
                key=param_name
            )
        elif ui_type == "list":
            return gr.Textbox(
                label=f"{label} (comma-separated)",
                value=",".join(default_value) if default_value else "",
                key=param_name
            )
        else:
            return gr.Textbox(
                label=label,
                value=str(default_value) if default_value else "",
                key=param_name
            )
    
    def create_pipeline_selection_interface(self) -> gr.Interface:
        """Create the main pipeline selection and configuration interface."""
        
        with gr.Blocks(theme=self.create_custom_theme(), title="Apiana AI Pipeline Runner") as interface:
            
            gr.Markdown("""
            # 🚀 Apiana AI Pipeline Runner
            
            Automatically discovered pipelines with real-time execution tracking.
            """)
            
            with gr.Tabs():
                # Pipeline Categories
                categories = self.discovery.get_pipelines_by_category()
                
                for category, pipeline_names in categories.items():
                    with gr.TabItem(category):
                        
                        # Pipeline selection
                        pipeline_dropdown = gr.Dropdown(
                            choices=pipeline_names,
                            label="Select Pipeline",
                            value=pipeline_names[0] if pipeline_names else None
                        )
                        
                        # Pipeline description
                        pipeline_description = gr.Markdown("")
                        
                        # Dynamic parameter inputs container
                        parameter_inputs = gr.Column(visible=False)
                        
                        # Neo4j configuration (common to most pipelines)
                        with gr.Group(visible=False) as neo4j_group:
                            gr.Markdown("### Neo4j Configuration")
                            # neo4j_inputs = self.create_neo4j_config_inputs()  # Unused for now
                            pass
                        
                        # Pipeline-specific parameters
                        dynamic_inputs = gr.Column()
                        
                        # Execution controls
                        with gr.Row():
                            # execute_btn = gr.Button("Execute Pipeline", variant="primary", size="lg")
                            # clear_btn = gr.Button("Clear Logs", variant="secondary")
                            pass
                        
                        # Execution status and progress
                        with gr.Group():
                            gr.Markdown("### Execution Status")
                            
                            with gr.Row():
                                # status_indicator = gr.Textbox(
                                #     label="Status",
                                #     value="Ready",
                                #     interactive=False
                                # )
                                # progress_bar = gr.Progress()
                                pass
                            
                            # Pipeline steps display
                            steps_display = gr.Markdown("### Pipeline Steps\n*Select a pipeline to see processing steps*")
                            
                            # Expandable logs section
                            with gr.Accordion("Execution Logs", open=False):
                                # logs_display = gr.Textbox(
                                #     label="",
                                #     value="",
                                #     lines=15,
                                #     max_lines=30,
                                #     interactive=False,
                                #     container=False,
                                #     elem_classes=["log-display"]
                                # )
                                pass
                        
                        # Results section
                        results_section = gr.Group(visible=False)
                        with results_section:
                            gr.Markdown("### Execution Results")
                            # results_display = gr.JSON(label="Pipeline Results")  # Unused for now
                            pass
                        
                        # Event handlers
                        def on_pipeline_select(pipeline_name):
                            if not pipeline_name:
                                return (
                                    "", 
                                    gr.update(visible=False),
                                    gr.update(visible=False),
                                    gr.update(value="*Select a pipeline to see processing steps*"),
                                    gr.update(children=[])
                                )
                            
                            metadata = self.discovery.get_pipeline_metadata(pipeline_name)
                            parameters = self.discovery.get_pipeline_parameters(pipeline_name)
                            
                            # Update description
                            description_md = f"""
                            ### {metadata.name}
                            
                            **Description:** {metadata.description}
                            
                            **Estimated Time:** {metadata.estimated_time}
                            
                            **Output:** {metadata.output_description}
                            
                            **Tags:** {', '.join(metadata.tags)}
                            """
                            
                            # Show Neo4j config if needed
                            needs_neo4j = "neo4j_config" in parameters
                            
                            # Create dynamic inputs
                            param_components = []
                            for param_name, param_info in parameters.items():
                                if param_name != "neo4j_config":  # Handle separately
                                    component = self.create_parameter_input(param_name, param_info)
                                    param_components.append(component)
                            
                            # Create steps display
                            steps_md = "### Pipeline Steps\n"
                            # This would be enhanced to show actual pipeline components
                            steps = ["Input Validation", "Data Processing", "Storage", "Completion"]
                            for i, step in enumerate(steps, 1):
                                steps_md += f"{i}. **{step}** ⏳\n"
                            
                            return (
                                description_md,
                                gr.update(visible=True),
                                gr.update(visible=needs_neo4j),
                                steps_md,
                                gr.update(children=param_components)
                            )
                        
                        pipeline_dropdown.change(
                            on_pipeline_select,
                            inputs=[pipeline_dropdown],
                            outputs=[
                                pipeline_description,
                                parameter_inputs,
                                neo4j_group,
                                steps_display,
                                dynamic_inputs
                            ]
                        )
                        
                        # Initialize with first pipeline if available
                        if pipeline_names:
                            interface.load(
                                lambda: on_pipeline_select(pipeline_names[0]),
                                outputs=[
                                    pipeline_description,
                                    parameter_inputs,
                                    neo4j_group,
                                    steps_display,
                                    dynamic_inputs
                                ]
                            )
        
        return interface
    
    def create_execution_interface(self) -> gr.Interface:
        """Create a simplified interface focused on execution monitoring."""
        
        def execute_pipeline(pipeline_name, *args):
            """Execute the selected pipeline with given parameters."""
            try:
                # This would be implemented to handle actual execution
                return "Pipeline execution started...", "running"
            except Exception as e:
                return f"Error: {str(e)}", "error"
        
        def get_logs():
            """Get current execution logs."""
            return self.executor.get_status().get("logs", "")
        
        def clear_logs():
            """Clear execution logs."""
            self.executor.execution_logs.clear_logs()
            return ""
        
        # Create the interface
        interface = gr.Interface(
            fn=execute_pipeline,
            inputs=[
                gr.Dropdown(
                    choices=self.discovery.get_pipeline_names(),
                    label="Pipeline"
                )
            ],
            outputs=[
                gr.Textbox(label="Status"),
                gr.Textbox(label="Execution State")
            ],
            title="Pipeline Executor",
            theme=self.create_custom_theme()
        )
        
        return interface