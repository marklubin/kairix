"""
Unit tests for base component interfaces.
"""

from typing import List

from apiana.core.components.common import Component, ComponentResult
from apiana.core.components.readers.base import Reader
from apiana.core.components.transform.base import Transform as Processor
from apiana.core.components.writers.base import Writer
from apiana.core.components.chunkers.base import Chunker


class TestComponentResult:
    """Test ComponentResult class."""
    
    def test_component_result_creation(self):
        """Test basic ComponentResult creation."""
        result = ComponentResult(data="test_data")
        assert result.data == "test_data"
        assert result.success is True
        assert result.errors == []
        assert result.warnings == []
        assert result.metadata == {}
    
    def test_component_result_with_errors(self):
        """Test ComponentResult with errors."""
        result = ComponentResult(data=None, errors=["error1", "error2"])
        assert result.success is False
        assert len(result.errors) == 2
    
    def test_add_error(self):
        """Test adding errors."""
        result = ComponentResult(data="test")
        assert result.success is True
        
        result.add_error("Something went wrong")
        assert result.success is False
        assert "Something went wrong" in result.errors
    
    def test_add_warning(self):
        """Test adding warnings."""
        result = ComponentResult(data="test")
        result.add_warning("Warning message")
        assert "Warning message" in result.warnings
        assert result.success is True  # Warnings don't affect success


class MockComponent(Component):
    """Mock component for testing."""
    
    def __init__(self, name: str, should_fail: bool = False, config: dict = None):
        super().__init__(name, config)
        self.should_fail = should_fail
        self.process_called = False
    
    def process(self, input_data):
        self.process_called = True
        if self.should_fail:
            return ComponentResult(data=None, errors=["Mock error"])
        return ComponentResult(data=f"processed_{input_data}")
    
    def validate_input(self, input_data) -> List[str]:
        if input_data is None:
            return ["Input cannot be None"]
        return []


class TestComponent:
    """Test base Component class."""
    
    def test_component_creation(self):
        """Test component creation."""
        comp = MockComponent("test_component")
        assert comp.name == "test_component"
        assert comp.config == {}
    
    def test_component_with_config(self):
        """Test component with configuration."""
        config = {"param1": "value1", "param2": 42}
        comp = MockComponent("test", config=config)
        assert comp.config == config
    
    def test_component_process(self):
        """Test component processing."""
        comp = MockComponent("test")
        result = comp.process("input_data")
        assert comp.process_called
        assert result.success
        assert result.data == "processed_input_data"
    
    def test_component_process_failure(self):
        """Test component processing failure."""
        comp = MockComponent("test", should_fail=True)
        result = comp.process("input_data")
        assert not result.success
        assert "Mock error" in result.errors
    
    def test_component_validation(self):
        """Test input validation."""
        comp = MockComponent("test")
        
        # Valid input
        errors = comp.validate_input("valid_data")
        assert errors == []
        
        # Invalid input
        errors = comp.validate_input(None)
        assert "Input cannot be None" in errors
    
    def test_component_string_representation(self):
        """Test string representations."""
        comp = MockComponent("test_component")
        assert "test_component" in str(comp)
        assert "MockComponent" in str(comp)


class MockReader(Reader):
    """Mock reader for testing."""
    
    def read(self, source: str):
        if source == "error":
            return ComponentResult(data=None, errors=["Read failed"])
        return ComponentResult(data=f"read_from_{source}")


class MockProcessor(Processor):
    """Mock processor for testing."""
    
    def transform(self, data):
        if data == "error":
            return ComponentResult(data=None, errors=["Transform failed"])
        return ComponentResult(data=f"transformed_{data}")


class MockWriter(Writer):
    """Mock writer for testing."""
    
    def write(self, data, destination: str):
        if destination == "error":
            return ComponentResult(data=None, errors=["Write failed"])
        return ComponentResult(data=f"written_{data}_to_{destination}")


class MockChunker(Chunker):
    """Mock chunker for testing."""
    
    def chunk(self, data):
        if data == "error":
            return ComponentResult(data=None, errors=["Chunk failed"])
        # Simulate chunking by splitting data
        chunks = [f"chunk_{i}_{data}" for i in range(2)]
        return ComponentResult(data=chunks)


class TestSpecializedComponents:
    """Test specialized component base classes."""
    
    def test_reader_component(self):
        """Test Reader base class."""
        reader = MockReader("test_reader")
        
        # Test successful read
        result = reader.process("test_source")
        assert result.success
        assert result.data == "read_from_test_source"
        
        # Test failed read
        result = reader.process("error")
        assert not result.success
    
    def test_processor_component(self):
        """Test Processor base class."""
        processor = MockProcessor("test_processor")
        
        # Test successful transform
        result = processor.process("test_data")
        assert result.success
        assert result.data == "transformed_test_data"
        
        # Test failed transform
        result = processor.process("error")
        assert not result.success
    
    def test_writer_component(self):
        """Test Writer base class."""
        writer = MockWriter("test_writer")
        
        # Test successful write
        result = writer.process(("test_data", "test_dest"))
        assert result.success
        assert result.data == "written_test_data_to_test_dest"
        
        # Test failed write
        result = writer.process(("test_data", "error"))
        assert not result.success
    
    def test_chunker_component(self):
        """Test Chunker base class."""
        chunker = MockChunker("test_chunker")
        
        # Test successful chunking
        result = chunker.process("test_data")
        assert result.success
        assert len(result.data) == 2
        assert "chunk_0_test_data" in result.data
        assert "chunk_1_test_data" in result.data
        
        # Test failed chunking
        result = chunker.process("error")
        assert not result.success