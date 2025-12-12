"""
Unit tests for reader components.
"""

import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from apiana.core.components import (
    ChatGPTExportReader,
    PlainTextReader,
    FragmentListReader
)
from apiana.types.chat_fragment import ChatFragment


class TestChatGPTExportReader:
    """Test ChatGPT export reader component."""
    
    def test_reader_creation(self):
        """Test reader creation."""
        reader = ChatGPTExportReader()
        assert reader.name == "chatgpt_export_reader"
    
    def test_validate_input_valid_file(self):
        """Test input validation with valid file."""
        reader = ChatGPTExportReader()
        
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            temp_path = f.name
        
        try:
            errors = reader.validate_input(temp_path)
            assert errors == []
        finally:
            Path(temp_path).unlink()
    
    def test_validate_input_invalid_file(self):
        """Test input validation with invalid inputs."""
        reader = ChatGPTExportReader()
        
        # Non-existent file
        errors = reader.validate_input("/nonexistent/file.json")
        assert "does not exist" in errors[0]
        
        # Non-JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("not json")
            temp_path = f.name
        
        try:
            errors = reader.validate_input(temp_path)
            assert "must be a JSON file" in errors[0]
        finally:
            Path(temp_path).unlink()
        
        # Invalid input type
        errors = reader.validate_input(123)
        assert "must be a file path" in errors[0]
    
    @patch('apiana.core.components.readers.chatgpt.ChatGPTExportReader._load_chatgpt_export')
    def test_read_success(self, mock_load):
        """Test successful reading."""
        # Mock the load function
        mock_fragments = [
            ChatFragment(title="Test 1", messages=[{"role": "user", "content": "Hello"}]),
            ChatFragment(title="Test 2", messages=[{"role": "assistant", "content": "Hi"}])
        ]
        mock_load.return_value = mock_fragments
        
        reader = ChatGPTExportReader()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            temp_path = f.name
        
        try:
            result = reader.read(temp_path)
            assert result.success
            assert len(result.data) == 2
            assert result.metadata['fragments_loaded'] == 2
            assert result.metadata['total_messages'] == 2
            mock_load.assert_called_once_with(temp_path)
        finally:
            Path(temp_path).unlink()
    
    @patch('apiana.core.components.readers.chatgpt.ChatGPTExportReader._load_chatgpt_export')
    def test_read_failure(self, mock_load):
        """Test read failure."""
        mock_load.side_effect = Exception("Failed to process file")
        
        reader = ChatGPTExportReader()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json")
            temp_path = f.name
        
        try:
            result = reader.read(temp_path)
            assert not result.success
            assert "Failed to load ChatGPT export" in result.errors[0]
        finally:
            Path(temp_path).unlink()


class TestPlainTextReader:
    """Test plain text reader component."""
    
    def test_reader_creation(self):
        """Test reader creation."""
        reader = PlainTextReader()
        assert reader.name == "plain_text_reader"
    
    def test_validate_input_valid_path(self):
        """Test input validation with valid paths."""
        reader = PlainTextReader()
        
        # Valid file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            errors = reader.validate_input(temp_path)
            assert errors == []
        finally:
            Path(temp_path).unlink()
    
    def test_validate_input_invalid_path(self):
        """Test input validation with invalid paths."""
        reader = PlainTextReader()
        
        # Non-existent path
        errors = reader.validate_input("/nonexistent/path")
        assert "does not exist" in errors[0]
        
        # Invalid input type
        errors = reader.validate_input(123)
        assert "must be a file or directory path" in errors[0]
    
    @patch.object(ChatFragment, 'from_file')
    def test_read_single_file(self, mock_from_file):
        """Test reading a single text file."""
        mock_fragment = ChatFragment(title="Test", messages=[{"role": "user", "content": "Hello"}])
        mock_from_file.return_value = mock_fragment
        
        reader = PlainTextReader()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            result = reader.read(temp_path)
            assert result.success
            assert len(result.data) == 1
            assert result.metadata['source_type'] == 'file'
            mock_from_file.assert_called_once()
        finally:
            Path(temp_path).unlink()
    
    @patch.object(ChatFragment, 'from_file')
    def test_read_directory(self, mock_from_file):
        """Test reading a directory of text files."""
        mock_fragment = ChatFragment(title="Test", messages=[{"role": "user", "content": "Hello"}])
        mock_from_file.return_value = mock_fragment
        
        reader = PlainTextReader()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            for i in range(3):
                file_path = Path(temp_dir) / f"test_{i}.txt"
                file_path.write_text(f"content {i}")
            
            result = reader.read(temp_dir)
            assert result.success
            assert len(result.data) == 3
            assert result.metadata['source_type'] == 'directory'
            assert mock_from_file.call_count == 3


class TestFragmentListReader:
    """Test fragment list reader component."""
    
    def test_reader_creation(self):
        """Test reader creation."""
        reader = FragmentListReader()
        assert reader.name == "fragment_list_reader"
    
    def test_validate_input_valid_list(self):
        """Test input validation with valid fragment list."""
        reader = FragmentListReader()
        
        fragments = [
            ChatFragment(title="Test 1", messages=[]),
            ChatFragment(title="Test 2", messages=[])
        ]
        
        errors = reader.validate_input(fragments)
        assert errors == []
    
    def test_validate_input_invalid_list(self):
        """Test input validation with invalid inputs."""
        reader = FragmentListReader()
        
        # Not a list
        errors = reader.validate_input("not a list")
        assert "must be a list" in errors[0]
        
        # List with non-ChatFragment items
        errors = reader.validate_input([ChatFragment(), "not a fragment", 123])
        assert len(errors) == 2
        assert "not a ChatFragment" in errors[0]
        assert "not a ChatFragment" in errors[1]
    
    def test_read_success(self):
        """Test successful reading of fragment list."""
        reader = FragmentListReader()
        
        fragments = [
            ChatFragment(title="Test 1", messages=[{"role": "user", "content": "Hello"}]),
            ChatFragment(title="Test 2", messages=[{"role": "assistant", "content": "Hi"}])
        ]
        
        result = reader.read(fragments)
        assert result.success
        assert result.data == fragments
        assert result.metadata['fragments_count'] == 2
        assert result.metadata['total_messages'] == 2
        assert result.metadata['source_type'] == 'fragment_list'