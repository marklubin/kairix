"""
Unit tests for PipelineRunWriter component.
"""

from datetime import datetime
from unittest.mock import Mock, patch
import pytest

from apiana.core.components.writers.pipeline_run_writer import PipelineRunWriter
from apiana.types.configuration import Neo4jConfig


@pytest.fixture
def mock_store():
    """Create a mock ApplicationStore."""
    return Mock()


@pytest.fixture
def mock_pipeline_run():
    """Create a mock pipeline run node."""
    run = Mock()
    run.run_id = "test-run-123"
    run.name = "Test Run"
    return run


class TestPipelineRunWriter:
    """Unit tests for PipelineRunWriter."""

    def test_init_with_defaults(self, mock_store):
        """Should initialize with default values."""
        writer = PipelineRunWriter(
            store=mock_store,
            run_name="Test Pipeline"
        )
        
        assert writer.store == mock_store
        assert writer.run_name == "Test Pipeline"
        assert writer.run_id.startswith("run-")
        assert writer.run_config == {}
        assert writer.pipeline_run is None

    def test_init_with_custom_values(self, mock_store):
        """Should initialize with custom values."""
        config = {"param": "value"}
        writer = PipelineRunWriter(
            store=mock_store,
            run_name="Custom Pipeline",
            run_id="custom-run-123",
            config=config
        )
        
        assert writer.store == mock_store
        assert writer.run_name == "Custom Pipeline"
        assert writer.run_id == "custom-run-123"
        assert writer.run_config == config

    @patch('apiana.core.components.writers.pipeline_run_writer.ApplicationStore')
    def test_from_config(self, mock_store_class):
        """Should create writer from Neo4j configuration."""
        config = Neo4jConfig(
            username="test", password="test", host="localhost", port=7687
        )
        run_config = {"test": "value"}
        mock_store = Mock()
        mock_store_class.return_value = mock_store

        writer = PipelineRunWriter.from_config(
            config, 
            run_name="Test",
            run_id="test-123",
            run_config=run_config
        )

        mock_store_class.assert_called_once_with(config)
        assert writer.store == mock_store
        assert writer.run_name == "Test"
        assert writer.run_id == "test-123"
        assert writer.run_config == run_config

    def test_start_run_success(self, mock_store, mock_pipeline_run):
        """Should start pipeline run successfully."""
        mock_store.create_pipeline_run.return_value = mock_pipeline_run
        writer = PipelineRunWriter(
            store=mock_store,
            run_name="Test Pipeline",
            run_id="test-123",
            config={"param": "value"}
        )
        
        result = writer.start_run()
        
        assert result.success
        assert writer.pipeline_run == mock_pipeline_run
        assert writer.started_at is not None
        
        mock_store.create_pipeline_run.assert_called_once_with(
            run_id="test-123",
            name="Test Pipeline",
            config={"param": "value"}
        )
        
        # Check metadata
        assert result.metadata["run_id"] == "test-123"
        assert result.metadata["run_name"] == "Test Pipeline"
        assert result.metadata["action"] == "start_run"

    def test_start_run_failure(self, mock_store):
        """Should handle start run failure."""
        mock_store.create_pipeline_run.side_effect = Exception("Database error")
        writer = PipelineRunWriter(store=mock_store, run_name="Test")
        
        result = writer.start_run()
        
        assert not result.success
        assert len(result.errors) == 1
        assert "Database error" in result.errors[0]

    def test_complete_run_success(self, mock_store, mock_pipeline_run):
        """Should complete pipeline run successfully."""
        mock_store.complete_pipeline_run.return_value = mock_pipeline_run
        writer = PipelineRunWriter(store=mock_store, run_name="Test")
        writer.pipeline_run = mock_pipeline_run
        
        stats = {"processed": 10}
        errors = ["error1", "error2"]
        
        result = writer.complete_run(stats=stats, errors=errors)
        
        assert result.success
        mock_store.complete_pipeline_run.assert_called_once_with(
            run_id=writer.run_id,
            stats=stats,
            errors=errors
        )
        
        # Check metadata
        assert result.metadata["stats"] == stats
        assert result.metadata["error_count"] == 2
        assert result.metadata["action"] == "complete_run"

    def test_complete_run_no_active_run(self, mock_store):
        """Should handle completion when no active run."""
        writer = PipelineRunWriter(store=mock_store, run_name="Test")
        
        result = writer.complete_run()
        
        assert not result.success
        assert len(result.errors) == 1
        assert "No active pipeline run" in result.errors[0]

    def test_complete_run_failure(self, mock_store, mock_pipeline_run):
        """Should handle complete run failure."""
        mock_store.complete_pipeline_run.side_effect = Exception("Database error")
        writer = PipelineRunWriter(store=mock_store, run_name="Test")
        writer.pipeline_run = mock_pipeline_run
        
        result = writer.complete_run()
        
        assert not result.success
        assert len(result.errors) == 1
        assert "Database error" in result.errors[0]

    def test_link_fragments_success(self, mock_store, mock_pipeline_run):
        """Should link fragments successfully."""
        mock_store.link_fragments_to_run.return_value = 2
        writer = PipelineRunWriter(store=mock_store, run_name="Test")
        writer.pipeline_run = mock_pipeline_run
        
        fragment_ids = ["frag-1", "frag-2"]
        result = writer.link_fragments(fragment_ids)
        
        assert result.success
        mock_store.link_fragments_to_run.assert_called_once_with(
            writer.run_id, fragment_ids
        )
        
        # Check metadata
        assert result.metadata["fragments_linked"] == 2
        assert result.metadata["fragment_ids"] == fragment_ids
        assert result.metadata["action"] == "link_fragments"

    def test_link_fragments_no_active_run(self, mock_store):
        """Should handle fragment linking when no active run."""
        writer = PipelineRunWriter(store=mock_store, run_name="Test")
        
        result = writer.link_fragments(["frag-1"])
        
        assert not result.success
        assert len(result.errors) == 1
        assert "No active pipeline run" in result.errors[0]

    def test_link_fragments_failure(self, mock_store, mock_pipeline_run):
        """Should handle fragment linking failure."""
        mock_store.link_fragments_to_run.side_effect = Exception("Link error")
        writer = PipelineRunWriter(store=mock_store, run_name="Test")
        writer.pipeline_run = mock_pipeline_run
        
        result = writer.link_fragments(["frag-1"])
        
        assert not result.success
        assert len(result.errors) == 1
        assert "Link error" in result.errors[0]

    def test_process_with_active_run(self, mock_store, mock_pipeline_run):
        """Should process data with active run metadata."""
        writer = PipelineRunWriter(store=mock_store, run_name="Test")
        writer.pipeline_run = mock_pipeline_run
        
        test_data = {"key": "value"}
        result = writer.process(test_data)
        
        assert result.success
        assert result.data == test_data
        
        # Check metadata
        assert result.metadata["run_id"] == writer.run_id
        assert result.metadata["run_name"] == "Test"
        assert result.metadata["entity_type"] == "pipeline_run"

    def test_process_without_active_run(self, mock_store):
        """Should process data without active run metadata."""
        writer = PipelineRunWriter(store=mock_store, run_name="Test")
        
        test_data = {"key": "value"}
        result = writer.process(test_data)
        
        assert result.success
        assert result.data == test_data
        assert "run_id" not in result.metadata

    def test_write_method(self, mock_store):
        """Should support Writer interface write method."""
        writer = PipelineRunWriter(store=mock_store, run_name="Test")
        
        test_data = {"key": "value"}
        result = writer.write(test_data, destination="ignored")
        
        assert result.success
        assert result.data == test_data

    def test_type_specifications(self, mock_store):
        """Should have correct input/output type specifications."""
        writer = PipelineRunWriter(store=mock_store, run_name="Test")
        
        # Should accept any type
        from typing import Any
        assert Any in writer.input_types
        assert Any in writer.output_types