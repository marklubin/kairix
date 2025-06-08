import json
import tempfile
from pathlib import Path

import pytest
from kairix_core.types import SourceDocument
from kairix_offline.processing.gpt_loader import (
    load_sources_from_gpt_export,
    parse_mapping,
)


@pytest.mark.integration
class TestGPTLoaderIntegration:
    """Integration tests for GPT loader with real Neo4j database"""

    @pytest.fixture
    def sample_conversation_data(self):
        """Create sample ChatGPT export data"""
        return [
            {
                "title": "Test Conversation 1",
                "mapping": {
                    "msg1": {
                        "message": {
                            "content": {"parts": ["Hello, how can I help you today?"]},
                            "author": {"role": "assistant"},
                            "create_time": 1234567890,
                        }
                    },
                    "msg2": {
                        "message": {
                            "content": {
                                "parts": ["I need help with Python programming"]
                            },
                            "author": {"role": "user"},
                            "create_time": 1234567891,
                        }
                    },
                    "msg3": {
                        "message": {
                            "content": {
                                "parts": [
                                    "I'd be happy to help with Python!",
                                    "What specific topic?",
                                ]
                            },
                            "author": {"role": "assistant"},
                            "create_time": 1234567892,
                        }
                    },
                },
            },
            {
                "title": "Test Conversation 2",
                "mapping": {
                    "msg1": {
                        "message": {
                            "content": {"parts": ["Tell me about machine learning"]},
                            "author": {"role": "user"},
                            "create_time": 1234567900,
                        }
                    }
                },
            },
        ]

    def test_parse_mapping_valid(self):
        """Test parsing valid message mapping"""
        mapping = {
            "message": {
                "content": {"parts": ["Test message content"]},
                "author": {"role": "user"},
                "create_time": 1234567890,
            }
        }

        result = parse_mapping(mapping)
        assert result is not None
        assert "Test message content" in result
        assert "user" in result
        assert "1234567890" in result

    def test_parse_mapping_invalid(self):
        """Test parsing invalid message mappings"""
        # Test with non-dict
        assert parse_mapping("not a dict") is None

        # Test with missing message key
        assert parse_mapping({"other": "data"}) is None

        # Test with missing content
        assert parse_mapping({"message": {"other": "data"}}) is None

        # Test with missing parts
        assert parse_mapping({"message": {"content": {"other": "data"}}}) is None

    def test_load_sources_from_gpt_export_single_conversation(
        self, sample_conversation_data
    ):
        """Test loading a single conversation from file"""
        # Create a temporary file with one conversation
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([sample_conversation_data[0]], f)
            temp_file = f.name

        try:
            # Load the file
            messages = list(load_sources_from_gpt_export(temp_file))

            # Verify source documents were created
            docs = SourceDocument.nodes.filter(source_type="chatgpt")
            assert len(docs) == 1

            doc = docs[0]
            assert doc.source_label == "Test Conversation 1"
            assert "Hello, how can I help you today?" in doc.content
            assert "I need help with Python programming" in doc.content
            assert "I'd be happy to help with Python!" in doc.content

        finally:
            Path(temp_file).unlink()

    def test_load_sources_from_gpt_export_multiple_conversations(
        self, sample_conversation_data
    ):
        """Test loading multiple conversations from file"""
        # Create a temporary file with all conversations
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_conversation_data, f)
            temp_file = f.name

        try:
            # Load the file
            messages = list(load_sources_from_gpt_export(temp_file))

            # Verify source documents were created
            docs = SourceDocument.nodes.filter(source_type="chatgpt")
            assert len(docs) == 2

            # Verify conversation titles
            titles = [doc.source_label for doc in docs]
            assert "Test Conversation 1" in titles
            assert "Test Conversation 2" in titles

        finally:
            Path(temp_file).unlink()

    def test_load_sources_from_gpt_export_with_empty_title(self):
        """Test handling conversations with empty titles"""
        data = [
            {
                "title": "",
                "mapping": {
                    "msg1": {
                        "message": {
                            "content": {"parts": ["Test message"]},
                            "author": {"role": "user"},
                            "create_time": 1234567890,
                        }
                    }
                },
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_file = f.name

        try:
            # Load the file - should skip conversation with no title
            messages = list(load_sources_from_gpt_export(temp_file))

            # Verify no documents were created
            docs = SourceDocument.nodes.filter(source_type="chatgpt")
            assert len(docs) == 0

        finally:
            Path(temp_file).unlink()

    def test_load_sources_from_gpt_export_with_no_mappings(self):
        """Test handling conversations with no mappings"""
        data = [{"title": "Empty Conversation", "mapping": None}]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_file = f.name

        try:
            # Load the file - should skip conversation with no mappings
            messages = list(load_sources_from_gpt_export(temp_file))

            # Verify no documents were created
            docs = SourceDocument.nodes.filter(source_type="chatgpt")
            assert len(docs) == 0

        finally:
            Path(temp_file).unlink()

    def test_load_sources_from_gpt_export_list_input(self, sample_conversation_data):
        """Test loading file when input is a list"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([sample_conversation_data[0]], f)
            temp_file = f.name

        try:
            # Load the file with list input
            messages = list(load_sources_from_gpt_export([temp_file]))

            # Verify document was created
            docs = SourceDocument.nodes.filter(source_type="chatgpt")
            assert len(docs) == 1

        finally:
            Path(temp_file).unlink()

    def test_load_sources_from_gpt_export_empty_list(self):
        """Test handling empty file list"""
        messages = list(load_sources_from_gpt_export([]))

        # Should yield info message about no file selected
        assert any("No file selected" in str(msg) for msg in messages)

    def test_document_content_formatting(self, sample_conversation_data):
        """Test that document content is properly formatted"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([sample_conversation_data[0]], f)
            temp_file = f.name

        try:
            # Load the file
            messages = list(load_sources_from_gpt_export(temp_file))

            # Get the created document
            doc = SourceDocument.nodes.get(source_type="chatgpt")

            # Verify content formatting
            lines = doc.content.split("\n")
            assert any("assistant:" in line for line in lines)
            assert any("user:" in line for line in lines)
            assert any("1234567890" in line for line in lines)

        finally:
            Path(temp_file).unlink()

    def test_unique_document_ids(self, sample_conversation_data):
        """Test that each document gets a unique ID"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_conversation_data, f)
            temp_file = f.name

        try:
            # Load the file
            messages = list(load_sources_from_gpt_export(temp_file))

            # Get all created documents
            docs = SourceDocument.nodes.filter(source_type="chatgpt")

            # Verify all UIDs are unique
            uids = [doc.uid for doc in docs]
            assert len(uids) == len(set(uids))

            # Verify UIDs are valid URNs
            for uid in uids:
                assert uid.startswith("urn:uuid:")

        finally:
            Path(temp_file).unlink()
