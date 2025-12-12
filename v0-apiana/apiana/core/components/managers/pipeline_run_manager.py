"""
PipelineRunManager for transparent pipeline execution tracking.

This component provides first-class pipeline run tracking that can be integrated
into any pipeline to automatically capture execution metadata, statistics, and
fragment relationships.
"""

from typing import List, Any, Type, Optional, Dict
import uuid
from contextlib import contextmanager

from apiana.core.components.common import Component, ComponentResult
from apiana.core.components.writers.pipeline_run_writer import PipelineRunWriter
from apiana.stores import ApplicationStore
from apiana.types.chat_fragment import ChatFragment
from apiana.types.configuration import Neo4jConfig


class PipelineRunManager(Component):
    """
    Manager component for transparent pipeline execution tracking.
    
    This component wraps pipeline execution to automatically:
    - Create pipeline run records
    - Track execution statistics
    - Link processed fragments
    - Handle completion and error states
    - Provide transparent pass-through operation
    
    It's designed to be added to any pipeline as a transparent wrapper
    that doesn't interfere with normal pipeline flow.
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
        auto_link_fragments: bool = True,
        name: str = "PipelineRunManager",
        **kwargs
    ):
        """
        Initialize the PipelineRunManager.
        
        Args:
            store: ApplicationStore instance for run tracking
            run_name: Human-readable name for the pipeline run
            run_id: Optional run ID (auto-generated if not provided)
            config: Optional configuration data to store with the run
            auto_link_fragments: Whether to automatically link ChatFragments found in pipeline data
            name: Component name for identification
            **kwargs: Additional component configuration
        """
        super().__init__(name=name, **kwargs)
        self.store = store
        self.run_name = run_name
        self.run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
        self.run_config = config or {}
        self.auto_link_fragments = auto_link_fragments
        
        # Create the PipelineRunWriter for actual operations
        self.run_writer = PipelineRunWriter(
            store=store,
            run_name=run_name,
            run_id=self.run_id,
            config=self.run_config,
            name=f"{name}_Writer"
        )
        
        # Tracking state
        self.is_started = False
        self.is_completed = False
        self.execution_stats = {
            "components_processed": 0,
            "fragments_seen": 0,
            "errors_encountered": 0,
            "warnings_encountered": 0
        }
        self.fragment_ids = set()
        self.errors = []
        
    @classmethod
    def from_config(
        cls, 
        config: Neo4jConfig, 
        run_name: str,
        run_id: Optional[str] = None,
        run_config: Optional[Dict[str, Any]] = None,
        auto_link_fragments: bool = True,
        **kwargs
    ):
        """
        Create PipelineRunManager from Neo4j configuration.
        
        Args:
            config: Neo4j configuration
            run_name: Human-readable name for the pipeline run
            run_id: Optional run ID (auto-generated if not provided)
            run_config: Optional configuration data to store with the run
            auto_link_fragments: Whether to automatically link ChatFragments
            **kwargs: Additional component configuration
            
        Returns:
            PipelineRunManager instance
        """
        store = ApplicationStore(config)
        return cls(
            store=store, 
            run_name=run_name, 
            run_id=run_id, 
            config=run_config,
            auto_link_fragments=auto_link_fragments,
            **kwargs
        )
    
    def start_tracking(self) -> ComponentResult:
        """
        Start pipeline run tracking.
        
        Returns:
            ComponentResult indicating success/failure
        """
        if self.is_started:
            result = ComponentResult(data=None)
            result.add_warning("Pipeline run tracking already started")
            return result
        
        result = self.run_writer.start_run()
        if result.success:
            self.is_started = True
            self.logger.info(f"Started tracking pipeline run: {self.run_name} ({self.run_id})")
        
        return result
    
    def stop_tracking(self, additional_stats: Optional[Dict[str, Any]] = None) -> ComponentResult:
        """
        Stop pipeline run tracking and finalize the run record.
        
        Args:
            additional_stats: Optional additional statistics to include
            
        Returns:
            ComponentResult indicating success/failure
        """
        if not self.is_started:
            result = ComponentResult(data=None)
            result.add_warning("Pipeline run tracking was not started")
            return result
        
        if self.is_completed:
            result = ComponentResult(data=None)
            result.add_warning("Pipeline run tracking already completed")
            return result
        
        # Combine execution stats with any additional stats
        final_stats = self.execution_stats.copy()
        if additional_stats:
            final_stats.update(additional_stats)
        
        # Link fragments if auto-linking is enabled
        if self.auto_link_fragments and self.fragment_ids:
            link_result = self.run_writer.link_fragments(list(self.fragment_ids))
            if not link_result.success:
                self.errors.extend([f"Fragment linking: {error}" for error in link_result.errors])
        
        # Complete the run
        result = self.run_writer.complete_run(stats=final_stats, errors=self.errors)
        if result.success:
            self.is_completed = True
            self.logger.info(f"Completed tracking pipeline run: {self.run_name} ({self.run_id})")
        
        return result
    
    def track_data(self, data: Any) -> None:
        """
        Track data flowing through the pipeline.
        
        Args:
            data: Data to analyze and track
        """
        if not self.is_started:
            return
        
        # Extract and track ChatFragments if auto-linking is enabled
        if self.auto_link_fragments:
            fragments = self._extract_fragments(data)
            for fragment in fragments:
                self.fragment_ids.add(fragment.fragment_id)
            
            if fragments:
                self.execution_stats["fragments_seen"] += len(fragments)
    
    def track_component_result(self, result: ComponentResult) -> None:
        """
        Track component execution results.
        
        Args:
            result: ComponentResult to track
        """
        if not self.is_started:
            return
        
        self.execution_stats["components_processed"] += 1
        
        if result.errors:
            self.execution_stats["errors_encountered"] += len(result.errors)
            self.errors.extend(result.errors)
        
        if result.warnings:
            self.execution_stats["warnings_encountered"] += len(result.warnings)
    
    def _extract_fragments(self, data: Any) -> List[ChatFragment]:
        """
        Extract ChatFragments from various data structures.
        
        Args:
            data: Data to search for ChatFragments
            
        Returns:
            List of found ChatFragments
        """
        fragments = []
        
        if isinstance(data, ChatFragment):
            fragments.append(data)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, ChatFragment):
                    fragments.append(item)
                elif isinstance(item, dict) and 'fragment' in item:
                    fragment = item['fragment']
                    if isinstance(fragment, ChatFragment):
                        fragments.append(fragment)
        elif isinstance(data, dict):
            if 'fragment' in data and isinstance(data['fragment'], ChatFragment):
                fragments.append(data['fragment'])
            # Recursively search dict values
            for value in data.values():
                fragments.extend(self._extract_fragments(value))
        
        return fragments
    
    def process(self, input_data: Any) -> ComponentResult:
        """
        Process data while tracking pipeline execution.
        
        This method provides transparent pass-through while collecting
        metadata about the data flowing through the pipeline.
        
        Args:
            input_data: Any data to pass through and track
            
        Returns:
            ComponentResult with the original input data (pass-through)
        """
        result = ComponentResult(data=input_data)
        
        # Ensure tracking is started
        if not self.is_started:
            start_result = self.start_tracking()
            if not start_result.success:
                result.errors.extend(start_result.errors)
                result.warnings.extend(start_result.warnings)
        
        # Track the data
        self.track_data(input_data)
        
        # Always pass through the data
        result.data = input_data
        
        # Add tracking metadata
        result.metadata.update({
            "run_id": self.run_id,
            "run_name": self.run_name,
            "tracking_active": self.is_started,
            "fragments_tracked": len(self.fragment_ids),
            "entity_type": "pipeline_run_manager"
        })
        
        return result
    
    @contextmanager
    def track_execution(self):
        """
        Context manager for tracking pipeline execution.
        
        Usage:
            with manager.track_execution():
                # Execute pipeline
                result = pipeline.run(data)
        """
        try:
            if not self.is_started:
                start_result = self.start_tracking()
                if not start_result.success:
                    self.logger.error(f"Failed to start tracking: {start_result.errors}")
            
            yield self
            
        except Exception as e:
            self.errors.append(f"Pipeline execution error: {str(e)}")
            raise
        finally:
            if self.is_started and not self.is_completed:
                stop_result = self.stop_tracking()
                if not stop_result.success:
                    self.logger.error(f"Failed to stop tracking: {stop_result.errors}")
    
    def get_run_id(self) -> str:
        """Get the current run ID."""
        return self.run_id
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current execution statistics."""
        return self.execution_stats.copy()
    
    def get_fragment_ids(self) -> List[str]:
        """Get list of tracked fragment IDs."""
        return list(self.fragment_ids)