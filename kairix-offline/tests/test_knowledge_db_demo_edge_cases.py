import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

import sys
from knowledge_db_demo import (
    Unit,
    Relation,
    Extraction,
    extract_knowledge,
    dedupe_semantic_unit,
    process_knowledge,
    cypher_query,
)


sys.path.append("/Users/mark/kairix/kairix-offline/scripts")


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_extract_knowledge_with_empty_summary(self):
        """Test extraction with empty summary text"""
        mock_summary = Mock()
        mock_summary.summary_text = ""

        mock_result = Mock()
        mock_result.final_output = Extraction(relationships=None)

        with patch("knowledge_db_demo.Runner.run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result

            result = await extract_knowledge(mock_summary)

            # Should handle None relationships gracefully
            assert result == []

    @pytest.mark.asyncio
    async def test_extract_knowledge_with_none_relationships(self):
        """Test when agents return None relationships"""
        mock_summary = Mock()
        mock_summary.summary_text = "Test text"

        # Create results with None relationships
        world_result = Mock()
        world_result.final_output = Extraction(relationships=None)

        user_result = Mock()
        user_result.final_output = Extraction(relationships=[])

        assistant_result = Mock()
        assistant_result.final_output = Extraction(relationships=None)

        with patch("knowledge_db_demo.Runner.run", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [world_result, user_result, assistant_result]

            result = await extract_knowledge(mock_summary)

            # Should handle None gracefully and return empty list
            assert result == []

    def test_dedupe_with_special_characters_in_id(self):
        """Test deduplication with special characters in unit ID"""
        unit = Unit(
            type="entity",
            short_description="Test with special chars",
            id="test/id:with-special_chars@123",
        )

        with patch("knowledge_db_demo.SemanticUnit") as mock_class:
            mock_class.nodes.first_or_none.return_value = None
            mock_class.create.return_value = Mock()

            with patch("knowledge_db_demo.embedder.encode") as mock_encode:
                mock_encode.return_value = [0.1] * 128

                with patch("knowledge_db_demo.vector_search") as mock_search:
                    mock_search.return_value = []

                    result = dedupe_semantic_unit(unit)

                    # Should handle special characters properly
                    mock_class.create.assert_called_once()
                    assert mock_class.create.call_args[1]["uid"] == unit.id

    def test_dedupe_with_empty_description(self):
        """Test deduplication with empty description"""
        unit = Unit(type="entity", short_description="", id="empty_desc")

        with patch("knowledge_db_demo.SemanticUnit") as mock_class:
            mock_class.nodes.first_or_none.return_value = None
            mock_class.create.return_value = Mock()

            with patch("knowledge_db_demo.embedder.encode") as mock_encode:
                mock_encode.return_value = [0.1] * 128

                with patch("knowledge_db_demo.vector_search") as mock_search:
                    mock_search.return_value = []

                    result = dedupe_semantic_unit(unit)

                    # Should handle empty description
                    mock_class.create.assert_called_once_with(
                        uid=unit.id,
                        descriptions=[""],  # Empty description is preserved
                        type=unit.type,
                    )

    def test_vector_search_with_empty_results(self):
        """Test vector search when no results are returned"""
        with patch("knowledge_db_demo.db.cypher_query") as mock_query:
            mock_query.return_value = ([], None)

            results = vector_search([0.1] * 128, k=5)

            assert results == []

    @pytest.mark.asyncio
    async def test_process_knowledge_with_zero_limit(self):
        """Test process_knowledge with n_limit=0"""
        mock_summaries = [
            Mock(summary_text="Summary 1"),
            Mock(summary_text="Summary 2"),
        ]

        with patch("knowledge_db_demo.Summary") as mock_summary_class:
            mock_summary_class.nodes.all.return_value = mock_summaries

            with patch(
                "knowledge_db_demo.extract_knowledge", new_callable=AsyncMock
            ) as mock_extract:
                await process_knowledge(0)

                # Should process at least 1 summary (max(1, 0) = 1)
                assert mock_extract.call_count == 1

    @pytest.mark.asyncio
    async def test_process_knowledge_with_negative_limit(self):
        """Test process_knowledge with negative n_limit"""
        mock_summaries = [Mock(summary_text="Summary 1")]

        with patch("knowledge_db_demo.Summary") as mock_summary_class:
            mock_summary_class.nodes.all.return_value = mock_summaries

            with patch(
                "knowledge_db_demo.extract_knowledge", new_callable=AsyncMock
            ) as mock_extract:
                mock_extract.return_value = []

                await process_knowledge(-5)

                # Should process at least 1 summary (max(1, -5) = 1)
                assert mock_extract.call_count == 1


class TestConcurrencyAndPerformance:
    """Test concurrent operations and performance scenarios"""

    @pytest.mark.asyncio
    async def test_extract_knowledge_concurrent_agent_execution(self):
        """Verify that agents run concurrently"""
        mock_summary = Mock()
        mock_summary.summary_text = "Test concurrent execution"

        execution_times = []

        async def mock_agent_execution(agent, text):
            start_time = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)  # Simulate work
            end_time = asyncio.get_event_loop().time()
            execution_times.append((start_time, end_time))

            result = Mock()
            result.final_output = Extraction(relationships=[])
            return result

        with patch("knowledge_db_demo.Runner.run", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = mock_agent_execution

            start = asyncio.get_event_loop().time()
            await extract_knowledge(mock_summary)
            end = asyncio.get_event_loop().time()

            # Total time should be ~0.1s (concurrent) not ~0.3s (sequential)
            total_time = end - start
            assert total_time < 0.2  # Allow some overhead

            # Verify all agents started roughly at the same time
            start_times = [t[0] for t in execution_times]
            assert max(start_times) - min(start_times) < 0.01

    @pytest.mark.asyncio
    async def test_process_knowledge_handles_large_extraction_sets(self):
        """Test processing with many extracted relationships"""
        # Create a large number of relationships
        large_relations = []
        for i in range(100):
            u = Unit(type="entity", short_description=f"Entity {i}", id=f"entity_{i}")
            v = Unit(type="attribute", short_description=f"Attr {i}", id=f"attr_{i}")
            large_relations.append(
                Relation(u=u, v=v, relationship_descriptor=f"rel_{i}")
            )

        mock_summary = Mock(summary_text="Large extraction test")

        with patch("knowledge_db_demo.Summary") as mock_summary_class:
            mock_summary_class.nodes.all.return_value = [mock_summary]

            with patch(
                "knowledge_db_demo.extract_knowledge", new_callable=AsyncMock
            ) as mock_extract:
                mock_extract.return_value = large_relations

                with patch("knowledge_db_demo.dedupe_semantic_unit") as mock_dedupe:
                    mock_unit = Mock()
                    mock_unit.relates = Mock()
                    mock_unit.relates.relationship.return_value = None
                    mock_unit.relates.connect = Mock()
                    mock_dedupe.return_value = mock_unit

                    await process_knowledge(1)

                    # Should handle all relationships
                    assert mock_dedupe.call_count == 200  # 100 relations * 2 units each
                    assert mock_unit.relates.connect.call_count == 100


class TestDataValidation:
    """Test data validation and type safety"""

    def test_unit_type_validation(self):
        """Test that Unit type is properly validated"""
        # Valid types should work
        for valid_type in ["entity", "action", "attribute", "topic", "event"]:
            unit = Unit(type=valid_type, short_description="Test", id="test")
            assert unit.type == valid_type

        # Invalid type should raise validation error
        with pytest.raises(ValueError):
            Unit(type="invalid_type", short_description="Test", id="test")

    def test_relation_missing_fields(self):
        """Test Relation with missing required fields"""
        u = Unit(type="entity", short_description="Test", id="test")

        # Should fail without all required fields
        with pytest.raises(TypeError):
            Relation(u=u)  # Missing v and relationship_descriptor

    def test_extraction_with_invalid_relationships(self):
        """Test Extraction with invalid relationship data"""
        # Should accept None
        extraction = Extraction(relationships=None)
        assert extraction.facts is None

        # Should accept empty list
        extraction = Extraction(relationships=[])
        assert extraction.facts == []


class TestDatabaseInteractions:
    """Test database-specific edge cases"""

    def test_cypher_query_wrapper(self):
        """Test the cypher_query wrapper function"""
        with patch("knowledge_db_demo.db.cypher_query") as mock_cypher:
            mock_cypher.return_value = (["result"], {"metadata": "test"})

            # Note: The function in the script takes 'self' but doesn't use it
            # This appears to be a bug in the original code
            result = cypher_query(None, "MATCH (n) RETURN n", {"param": "value"})

            assert result == (["result"], {"metadata": "test"})
            mock_cypher.assert_called_once_with(
                "MATCH (n) RETURN n", {"param": "value"}
            )

    def test_vector_search_malformed_results(self):
        """Test vector search with malformed database results"""
        with patch("knowledge_db_demo.db.cypher_query") as mock_query:
            # Return results with unexpected format
            mock_query.return_value = ([("malformed", None), (None, 0.5)], None)

            # Should handle gracefully
            with pytest.raises(IndexError):
                vector_search([0.1] * 128, k=2)

    @pytest.mark.asyncio
    async def test_process_knowledge_database_connection_failure(self):
        """Test handling of database connection failures"""
        mock_summary = Mock(summary_text="Test")

        with patch("knowledge_db_demo.Summary") as mock_summary_class:
            # Simulate database connection failure
            mock_summary_class.nodes.all.side_effect = Exception(
                "Database connection failed"
            )

            with pytest.raises(Exception) as exc_info:
                await process_knowledge(1)

            assert "Database connection failed" in str(exc_info.value)


class TestMemoryLeaksAndCleanup:
    """Test for potential memory leaks and resource cleanup"""

    @pytest.mark.asyncio
    async def test_large_embedding_handling(self):
        """Test handling of large embeddings"""
        unit = Unit(
            type="entity", short_description="Test large embedding", id="large_embed"
        )

        with patch("knowledge_db_demo.SemanticUnit") as mock_class:
            mock_class.nodes.first_or_none.return_value = None

            with patch("knowledge_db_demo.embedder.encode") as mock_encode:
                # Return very large embedding
                mock_encode.return_value = [0.1] * 10000

                with patch("knowledge_db_demo.vector_search") as mock_search:
                    mock_search.return_value = []

                    mock_new_unit = Mock()
                    mock_class.create.return_value = mock_new_unit

                    result = dedupe_semantic_unit(unit)

                    # Should handle large embeddings
                    mock_new_unit.save.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
