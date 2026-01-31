"""Unit tests for the Memory Scopes system.

These tests focus on schema validation and service function logic
without requiring a database connection.

Run with: uv run pytest tests/test_scopes.py -v
"""

from uuid import uuid4

import pytest

from kp3.schemas.scope import (
    MemoryScopeCreate,
    ScopeAddRequest,
    ScopeDefinition,
    ScopedPassageCreate,
    ScopeRemoveRequest,
    ScopeRevertRequest,
)

# =============================================================================
# ScopeDefinition schema tests
# =============================================================================


class TestScopeDefinition:
    """Tests for ScopeDefinition Pydantic model."""

    def test_empty_definition(self) -> None:
        """Test creating an empty scope definition."""
        scope_def = ScopeDefinition()
        assert scope_def.refs == []
        assert scope_def.passages == []
        assert scope_def.version == 1
        assert scope_def.created_from is None

    def test_definition_with_refs(self) -> None:
        """Test creating a scope definition with refs."""
        scope_def = ScopeDefinition(
            refs=["agent/human/HEAD", "agent/persona/HEAD"],
            version=3,
        )
        assert scope_def.refs == ["agent/human/HEAD", "agent/persona/HEAD"]
        assert scope_def.passages == []
        assert scope_def.version == 3

    def test_definition_with_passages(self) -> None:
        """Test creating a scope definition with passage IDs."""
        pid1 = uuid4()
        pid2 = uuid4()
        scope_def = ScopeDefinition(
            passages=[pid1, pid2],
            version=5,
        )
        assert len(scope_def.passages) == 2
        assert pid1 in scope_def.passages
        assert pid2 in scope_def.passages

    def test_definition_with_lineage(self) -> None:
        """Test creating a scope definition with lineage tracking."""
        prev_id = uuid4()
        scope_def = ScopeDefinition(
            refs=["agent/world/HEAD"],
            passages=[uuid4()],
            version=10,
            created_from=prev_id,
        )
        assert scope_def.created_from == prev_id
        assert scope_def.version == 10

    def test_definition_json_roundtrip(self) -> None:
        """Test JSON serialization and deserialization."""
        pid = uuid4()
        prev_id = uuid4()
        original = ScopeDefinition(
            refs=["ref1", "ref2"],
            passages=[pid],
            version=42,
            created_from=prev_id,
        )

        json_str = original.model_dump_json()
        restored = ScopeDefinition.model_validate_json(json_str)

        assert restored.refs == original.refs
        assert restored.passages == original.passages
        assert restored.version == original.version
        assert restored.created_from == original.created_from


# =============================================================================
# Request schema tests
# =============================================================================


class TestMemoryScopeCreate:
    """Tests for MemoryScopeCreate request schema."""

    def test_minimal_create(self) -> None:
        """Test creating with just a name."""
        request = MemoryScopeCreate(name="working-memory")
        assert request.name == "working-memory"
        assert request.description is None

    def test_create_with_description(self) -> None:
        """Test creating with name and description."""
        request = MemoryScopeCreate(
            name="context",
            description="Active conversation context",
        )
        assert request.name == "context"
        assert request.description == "Active conversation context"

    def test_name_validation_empty(self) -> None:
        """Test that empty name is rejected."""
        with pytest.raises(ValueError):
            MemoryScopeCreate(name="")

    def test_name_validation_too_long(self) -> None:
        """Test that overly long name is rejected."""
        with pytest.raises(ValueError):
            MemoryScopeCreate(name="x" * 257)


class TestScopedPassageCreate:
    """Tests for ScopedPassageCreate request schema."""

    def test_minimal_create(self) -> None:
        """Test creating with required fields only."""
        request = ScopedPassageCreate(
            content="Test content",
            passage_type="memory",
        )
        assert request.content == "Test content"
        assert request.passage_type == "memory"
        assert request.metadata is None
        assert request.period_start is None
        assert request.period_end is None

    def test_content_validation_empty(self) -> None:
        """Test that empty content is rejected."""
        with pytest.raises(ValueError):
            ScopedPassageCreate(content="", passage_type="test")


class TestScopeAddRequest:
    """Tests for ScopeAddRequest schema."""

    def test_empty_request(self) -> None:
        """Test creating an empty add request."""
        request = ScopeAddRequest()
        assert request.passage_ids == []
        assert request.refs == []

    def test_add_passages_only(self) -> None:
        """Test adding only passages."""
        pid = uuid4()
        request = ScopeAddRequest(passage_ids=[pid])
        assert request.passage_ids == [pid]
        assert request.refs == []

    def test_add_refs_only(self) -> None:
        """Test adding only refs."""
        request = ScopeAddRequest(refs=["agent/human/HEAD"])
        assert request.passage_ids == []
        assert request.refs == ["agent/human/HEAD"]

    def test_add_both(self) -> None:
        """Test adding both passages and refs."""
        pid = uuid4()
        request = ScopeAddRequest(
            passage_ids=[pid],
            refs=["agent/human/HEAD", "agent/persona/HEAD"],
        )
        assert request.passage_ids == [pid]
        assert len(request.refs) == 2


class TestScopeRemoveRequest:
    """Tests for ScopeRemoveRequest schema."""

    def test_empty_request(self) -> None:
        """Test creating an empty remove request."""
        request = ScopeRemoveRequest()
        assert request.passage_ids == []
        assert request.refs == []

    def test_remove_passages(self) -> None:
        """Test removing passages."""
        pid1 = uuid4()
        pid2 = uuid4()
        request = ScopeRemoveRequest(passage_ids=[pid1, pid2])
        assert len(request.passage_ids) == 2

    def test_remove_refs(self) -> None:
        """Test removing refs."""
        request = ScopeRemoveRequest(refs=["old/ref"])
        assert request.refs == ["old/ref"]


class TestScopeRevertRequest:
    """Tests for ScopeRevertRequest schema."""

    def test_valid_version(self) -> None:
        """Test reverting to a valid version."""
        request = ScopeRevertRequest(to_version=5)
        assert request.to_version == 5

    def test_version_validation_zero(self) -> None:
        """Test that version 0 is rejected."""
        with pytest.raises(ValueError):
            ScopeRevertRequest(to_version=0)

    def test_version_validation_negative(self) -> None:
        """Test that negative version is rejected."""
        with pytest.raises(ValueError):
            ScopeRevertRequest(to_version=-1)


# =============================================================================
# Scope name/ref generation tests
# =============================================================================


class TestScopeNaming:
    """Tests for scope naming conventions."""

    def test_head_ref_format(self) -> None:
        """Test the expected head ref format."""
        agent_id = "test-agent"
        scope_name = "working-memory"
        expected_ref = f"{agent_id}/scope/{scope_name}/HEAD"
        assert expected_ref == "test-agent/scope/working-memory/HEAD"

    def test_scope_definition_type(self) -> None:
        """Test the scope definition passage type constant."""
        from kp3.services.scopes import SCOPE_DEFINITION_TYPE

        assert SCOPE_DEFINITION_TYPE == "scope_definition"
