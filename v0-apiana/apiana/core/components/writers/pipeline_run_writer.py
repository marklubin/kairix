"""
PipelineRunWriter component for tracking pipeline execution metadata.

This component creates and manages PipelineRun records in the ApplicationStore,
providing transparent execution tracking and metadata collection.
"""

from typing import List, Any, Type, Optional, Dict
import uuid
from datetime import datetime

from apiana.core.components.common import ComponentResult
from apiana.core.components.writers.base import Writer
from apiana.stores import ApplicationStore
from apiana.types.configuration import Neo4jConfig


class PipelineRunWriter(Writer):
    """
    Writer component for managing pipeline execution records.
    
    This component creates PipelineRun records at the start of pipeline execution
    and updates them with completion status and statistics. It's designed to be
    integrated transparently into pipeline execution.
    
    Key features:
    - Automatic run ID generation
    - Start/completion tracking
    - Statistics and error collection
    - Transparent pass-through operation
    """
    
    # Type specifications - accepts any data type for pass-through
    input_types: List[Type] = [Any]
    output_types: List[Type] = [Any]
    
    def __init__(
        self, 
        store: ApplicationStore, 
        run_name: str,
        run_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        name: str = "PipelineRunWriter",
        **kwargs
    ):
        """
        Initialize the PipelineRunWriter.
        
        Args:
            store: ApplicationStore instance for data persistence
            run_name: Human-readable name for the pipeline run
            run_id: Optional run ID (auto-generated if not provided)
            config: Optional configuration data to store with the run
            name: Component name for identification
            **kwargs: Additional component configuration
        """
        super().__init__(name=name, **kwargs)
        self.store = store
        self.run_name = run_name
        self.run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
        self.run_config = config or {}
        self.pipeline_run = None
        self.started_at = None
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    @classmethod
    def from_config(
        cls, 
        config: Neo4jConfig, 
        run_name: str,
        run_id: Optional[str] = None,
        run_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Create PipelineRunWriter from Neo4j configuration.
        
        Args:
            config: Neo4j configuration
            run_name: Human-readable name for the pipeline run
            run_id: Optional run ID (auto-generated if not provided)
            run_config: Optional configuration data to store with the run
            **kwargs: Additional component configuration
            
        Returns:
            PipelineRunWriter instance
        """
        store = ApplicationStore(config)
        return cls(
            store=store, 
            run_name=run_name, 
            run_id=run_id, 
            config=run_config, 
            **kwargs
        )
    
    def start_run(self) -> ComponentResult:
        """
        Start a new pipeline run record.
        
        Returns:
            ComponentResult indicating success/failure of run creation
        """
        result = ComponentResult(data=None)
        
        try:
            self.started_at = datetime.utcnow()
            self.pipeline_run = self.store.create_pipeline_run(
                run_id=self.run_id,
                name=self.run_name,
                config=self.run_config
            )
            
            result.metadata.update({
                "run_id": self.run_id,
                "run_name": self.run_name,
                "started_at": self.started_at.isoformat(),
                "action": "start_run"
            })
            
            self.logger.info(f"Started pipeline run '{self.run_name}' with ID: {self.run_id}")
            
        except Exception as e:
            result.add_error(f"Failed to start pipeline run: {str(e)}")
        
        return result
    
    def complete_run(
        self, 
        stats: Optional[Dict[str, Any]] = None, 
        errors: Optional[List[str]] = None
    ) -> ComponentResult:
        """
        Complete the pipeline run with final statistics.
        
        Args:
            stats: Optional statistics about the run
            errors: Optional list of errors that occurred
            
        Returns:
            ComponentResult indicating success/failure of run completion
        """
        result = ComponentResult(data=None)
        
        try:
            if not self.pipeline_run:
                result.add_error("No active pipeline run to complete")
                return result
            
            self.pipeline_run = self.store.complete_pipeline_run(
                run_id=self.run_id,
                stats=stats or {},
                errors=errors or []
            )
            
            result.metadata.update({
                "run_id": self.run_id,
                "run_name": self.run_name,
                "completed_at": datetime.utcnow().isoformat(),
                "stats": stats or {},
                "error_count": len(errors or []),
                "action": "complete_run"
            })
            
            status = "completed" if not errors else "failed"
            self.logger.info(f"Pipeline run '{self.run_name}' {status} with ID: {self.run_id}")
            
        except Exception as e:
            result.add_error(f"Failed to complete pipeline run: {str(e)}")
        
        return result
    
    def link_fragments(self, fragment_ids: List[str]) -> ComponentResult:
        """
        Link processed fragments to this pipeline run.
        
        Args:
            fragment_ids: List of ChatFragment IDs that were processed
            
        Returns:
            ComponentResult with linking information
        """
        result = ComponentResult(data=None)
        
        try:
            if not self.pipeline_run:
                result.add_error("No active pipeline run to link fragments to")
                return result
            
            linked_count = self.store.link_fragments_to_run(self.run_id, fragment_ids)
            
            result.metadata.update({
                "run_id": self.run_id,
                "fragments_linked": linked_count,
                "fragment_ids": fragment_ids,
                "action": "link_fragments"
            })
            
            self.logger.info(f"Linked {linked_count} fragments to run {self.run_id}")
            
        except Exception as e:
            result.add_error(f"Failed to link fragments: {str(e)}")
        
        return result
    
    def process(self, input_data: Any) -> ComponentResult:
        """
        Process data while tracking pipeline execution.
        
        This method simply passes through the input data while maintaining
        the pipeline run state. The actual run management is handled by
        separate methods.
        
        Args:
            input_data: Any data to pass through
            
        Returns:
            ComponentResult with the original input data (pass-through)
        """
        result = ComponentResult(data=input_data)
        
        # Add run metadata if available
        if self.pipeline_run:
            result.metadata.update({
                "run_id": self.run_id,
                "run_name": self.run_name,
                "entity_type": "pipeline_run"
            })
        
        return result
    
    def write(self, data: Any, destination: str = "default") -> ComponentResult:
        """
        Write method for Writer interface compatibility.
        
        Args:
            data: Data to pass through
            destination: Ignored (PipelineRun uses ApplicationStore)
            
        Returns:
            ComponentResult with data
        """
        return self.process(data)