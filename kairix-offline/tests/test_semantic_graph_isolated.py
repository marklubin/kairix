"""
Unit tests for semantic_graph.py script with mocked dependencies
"""

import sys
import os
from unittest.mock import AsyncMock, Mock, patch
import pytest

# Mock all the dependencies before importing anything else
sys.modules["sentence_transformers"] = Mock()
sys.modules["agents"] = Mock()

# Mock kairix_core modules
sys.modules["kairix_core"] = Mock()
sys.modules["kairix_core.runtime"] = Mock()
sys.modules["kairix_core.runtime.agent"] = Mock()
sys.modules["kairix_core.runtime.logging"] = Mock()
sys.modules["kairix_core.runtime.neo4j"] = Mock()
sys.modules["kairix_core.types"] = Mock()
sys.modules["kairix_core.types.neo4j"] = Mock()

# Set up environment variable
os.environ["KAIRIX_AGENT_CONFIGURATION_SET_KEY"] = "test"

# Create mock classes
MockConcept = Mock()
MockConcept.first_or_none = Mock()
MockConcept.vector_search = Mock()
MockSemanticLinkage = Mock()
MockSummary = Mock()
MockSummary.nodes = Mock()

# Assign to mocked module
sys.modules["kairix_core.types.neo4j"].Concept = MockConcept
sys.modules["kairix_core.types.neo4j"].SemanticLinkage = MockSemanticLinkage
sys.modules["kairix_core.types.neo4j"].Summary = MockSummary

# Mock runtime modules
sys.modules["kairix_core.runtime.agent"].AgentRuntime = Mock
sys.modules["kairix_core.runtime.logging"].LoggingRuntime = Mock
sys.modules["kairix_core.runtime.neo4j"].Neo4jRuntime = Mock

# Now we can import the types we need
from kairix_offline.semantic_graph.types import Extract, Fact, Subject  # noqa: E402

# Import semantic_graph after all mocks are set up
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import semantic_graph  # noqa: E402


class TestUpsertConcept:
    """Test cases for upsert_concept function"""

    def test_exact_match_exists(self):
        """Test Case I: Exact match exists - should increment occurrences"""
        # Given: An exact match exists in the database
        existing_concept = Mock()
        existing_concept.occurences = 1
        existing_concept.save = Mock()

        MockConcept.first_or_none.return_value = existing_concept

        subject = Subject(name="test_entity", type="person")

        # When: We try to upsert the same concept
        result = semantic_graph.upsert_concept(subject)

        # Then: The occurrences should be incremented and saved
        assert existing_concept.occurences == 2
        existing_concept.save.assert_called_once()
        assert result == existing_concept

    def test_embedding_match_close_enough(self):
        """Test Case II: Semantic match via embedding - should update existing"""
        # Given: No exact match but a close embedding match exists
        matching_concept = Mock()
        matching_concept.semantic_id = "person_similar_entity"
        matching_concept.type = "person"
        matching_concept.occurences = 1
        matching_concept.save = Mock()

        MockConcept.first_or_none.return_value = None
        MockConcept.vector_search.return_value = [(matching_concept, 0.85)]

        subject = Subject(name="test_entity", type="person")

        # When: We try to upsert a semantically similar concept
        result = semantic_graph.upsert_concept(subject)

        # Then: The existing concept should be updated
        assert matching_concept.occurences == 2
        matching_concept.save.assert_called_once()
        assert result == matching_concept

    def test_embedding_match_below_threshold(self):
        """Test Case II edge: Embedding match below threshold - should create new"""
        # Given: No exact match and embedding match is below threshold
        MockConcept.first_or_none.return_value = None
        MockConcept.vector_search.return_value = [(Mock(), 0.65)]

        new_concept = Mock()
        new_concept.save = Mock()
        MockConcept.return_value = new_concept

        subject = Subject(name="test_entity", type="person")

        # When: We try to upsert the concept
        result = semantic_graph.upsert_concept(subject)

        # Then: A new concept should be created
        new_concept.save.assert_called_once()
        assert result == new_concept

    def test_embedding_match_wrong_type(self):
        """Test Case II edge: Embedding match but wrong type - should create new"""
        # Given: No exact match and embedding match has different type
        wrong_type_concept = Mock()
        wrong_type_concept.type = "organization"

        MockConcept.first_or_none.return_value = None
        MockConcept.vector_search.return_value = [(wrong_type_concept, 0.85)]

        new_concept = Mock()
        new_concept.save = Mock()
        MockConcept.return_value = new_concept

        subject = Subject(name="test_entity", type="person")

        # When: We try to upsert the concept
        result = semantic_graph.upsert_concept(subject)

        # Then: A new concept should be created
        new_concept.save.assert_called_once()
        assert result == new_concept

    def test_new_concept_creation(self):
        """Test Case III: No match found - should create new concept"""
        # Given: No match exists
        MockConcept.first_or_none.return_value = None
        MockConcept.vector_search.return_value = []

        new_concept = Mock()
        new_concept.save = Mock()
        MockConcept.return_value = new_concept

        subject = Subject(name="test_entity", type="person")

        # When: We try to upsert a new concept
        result = semantic_graph.upsert_concept(subject)

        # Then: A new concept should be created with correct attributes
        MockConcept.assert_called_with(
            semantic_id="person_test_entity",
            name="test_entity",
            type="person",
            embedding=semantic_graph.embedder.encode.return_value.tolist.return_value,
        )
        new_concept.save.assert_called_once()
        assert result == new_concept


class TestUpsertLinkage:
    """Test cases for upsert_linkage function"""

    def test_new_linkage_creation(self):
        """Test creating a new linkage between concepts"""
        # Given: Two concepts with no existing linkage
        source_concept = Mock()
        source_concept.semantic_id = "person_test"
        source_concept.link = Mock()
        source_concept.link.all_relationships.return_value = []

        target_concept = Mock()
        target_concept.semantic_id = "org_test"

        # When: We create a linkage
        semantic_graph.upsert_linkage(source_concept, target_concept, "works_with")

        # Then: A new connection should be created
        source_concept.link.connect.assert_called_once_with(
            target_concept, {"linkage_type": "works_with"}
        )

    def test_existing_linkage_not_duplicated(self):
        """Test that existing linkage is not duplicated"""
        # Given: Two concepts with an existing linkage
        source_concept = Mock()
        source_concept.link = Mock()

        existing_linkage = Mock()
        existing_linkage.linkage_type = "works_with"
        source_concept.link.all_relationships.return_value = [existing_linkage]

        target_concept = Mock()

        # When: We try to create the same linkage
        semantic_graph.upsert_linkage(source_concept, target_concept, "works_with")

        # Then: No new connection should be created
        source_concept.link.connect.assert_not_called()


class TestUpdateSemanticGraphWithFacts:
    """Test cases for update_semantic_graph_with_facts function"""

    def test_successful_update(self):
        """Test successful update of semantic graph with facts"""
        # Given: A list of facts
        fact = Fact(
            s=Subject(name="person1", type="person"),
            t=Subject(name="org1", type="organization"),
            relationship="works_with",
        )

        mock_s_unit = Mock()
        mock_t_unit = Mock()

        # Mock the neo4j transaction context manager
        mock_transaction = Mock()
        mock_transaction.__enter__ = Mock(return_value=None)
        mock_transaction.__exit__ = Mock(return_value=None)
        semantic_graph.neo4j.transaction = Mock(return_value=mock_transaction)

        with patch.object(
            semantic_graph, "upsert_concept", side_effect=[mock_s_unit, mock_t_unit]
        ):
            with patch.object(semantic_graph, "upsert_linkage") as mock_linkage:
                # When: We update the semantic graph
                semantic_graph.update_semantic_graph_with_facts([fact])

                # Then: Concepts and linkages should be created
                mock_linkage.assert_called_once_with(
                    mock_s_unit, mock_t_unit, "works_with"
                )

    def test_exception_triggers_rollback(self):
        """Test that exceptions trigger database rollback"""
        # Given: An exception occurs during processing
        fact = Fact(
            s=Subject(name="person1", type="person"),
            t=Subject(name="org1", type="organization"),
            relationship="works_with",
        )

        # Mock the neo4j transaction context manager
        mock_transaction = Mock()
        mock_transaction.__enter__ = Mock(return_value=None)
        mock_transaction.__exit__ = Mock(return_value=None)
        semantic_graph.neo4j.transaction = Mock(return_value=mock_transaction)
        semantic_graph.neo4j.rollback = Mock()

        with patch.object(
            semantic_graph, "upsert_concept", side_effect=Exception("DB Error")
        ):
            # When/Then: Exception should be re-raised and rollback called
            with pytest.raises(Exception, match="DB Error"):
                semantic_graph.update_semantic_graph_with_facts([fact])

            semantic_graph.neo4j.rollback.assert_called_once()


class TestDoExtract:
    """Test cases for do_extract async function"""

    @pytest.mark.asyncio
    async def test_successful_extraction(self):
        """Test successful extraction from text"""
        # Given: Text and extraction agents
        text = "Test text for extraction"
        test_agents = [Mock(name="agent1"), Mock(name="agent2")]

        # Mock the agent runtime responses
        mock_result1 = Mock()
        mock_result1.final_output = Extract(
            facts=[
                Fact(
                    s=Subject(name="entity1", type="person"),
                    t=Subject(name="entity2", type="organization"),
                    relationship="works_with",
                )
            ]
        )

        mock_result2 = Mock()
        mock_result2.final_output = Extract(facts=[])

        semantic_graph.agent_runtime.run = AsyncMock(
            side_effect=[mock_result1, mock_result2]
        )

        # When: We extract facts
        result = await semantic_graph.do_extract(text, test_agents)

        # Then: All facts should be collected
        assert len(result) == 1
        assert semantic_graph.agent_runtime.run.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_extraction(self):
        """Test handling of empty extractions"""
        # Given: Agents that return empty extractions
        text = "Test text"
        test_agents = [Mock(name="agent1")]

        mock_result = Mock()
        mock_result.final_output = Extract(facts=[])

        semantic_graph.agent_runtime.run = AsyncMock(return_value=mock_result)

        # When: We extract facts
        result = await semantic_graph.do_extract(text, test_agents)

        # Then: Result should be empty
        assert len(result) == 0


class TestExtractFactsFromSummaries:
    """Test cases for extract_facts_from_summaries async function"""

    @pytest.mark.asyncio
    async def test_new_summary_processing(self):
        """Test processing of new summaries"""
        # Given: A new summary and cache
        summary = Mock()
        summary.uid = "test-123"
        summary.summary_text = "Test summary text"

        # Mock cache with dictionary-like behavior
        cache = Mock()
        # Mock getitem to return None initially, then "started" after first check
        cache_state = {"test-123": None}

        def get_item(key):
            return cache_state.get(key)

        def set_item(key, value):
            cache_state[key] = value

        cache.__getitem__ = Mock(side_effect=get_item)
        cache.__setitem__ = Mock(side_effect=set_item)

        extracted_facts = [
            Fact(
                s=Subject(name="test", type="person"),
                t=Subject(name="org", type="organization"),
                relationship="works_with",
            )
        ]

        with patch.object(
            semantic_graph, "do_extract", AsyncMock(return_value=extracted_facts)
        ):
            # When: We process summaries
            result = await semantic_graph.extract_facts_from_summaries([summary], cache)

            # Then: Facts should be extracted and cached
            assert len(result) == 1
            # Verify cache was updated
            cache.__setitem__.assert_any_call("test-123", "extracted")
            cache.__setitem__.assert_any_call("test-123::extractions", extracted_facts)

    @pytest.mark.asyncio
    async def test_cached_summary_skipped(self):
        """Test that already processed summaries are skipped"""
        # Given: A summary already marked as extracted in cache
        summary = Mock()
        summary.uid = "test-123"

        cache = {"test-123": "extracted"}

        with patch.object(semantic_graph, "do_extract", AsyncMock()) as mock_extract:
            # When: We process the summary
            result = await semantic_graph.extract_facts_from_summaries([summary], cache)

            # Then: Extraction should be skipped
            assert len(result) == 0
            mock_extract.assert_not_called()


class TestMain:
    """Test cases for main function with different commands"""

    @pytest.mark.asyncio
    async def test_summary_extraction_command(self):
        """Test main function with summary-extraction command"""
        # Given: Command line args for summary extraction
        with patch("argparse.ArgumentParser.parse_args") as mock_parse:
            mock_args = Mock()
            mock_args.command = "summary-extraction"
            mock_parse.return_value = mock_args

            with patch("diskcache.Cache") as mock_cache_class:
                mock_extraction_cache = Mock()
                mock_fact_cache = Mock()
                mock_extraction_cache.close = Mock()
                mock_fact_cache.close = Mock()
                mock_cache_class.side_effect = [mock_extraction_cache, mock_fact_cache]

                mock_summaries = [Mock(uid="test1", summary_text="Test")]
                extracted_facts = [Mock()]

                with patch.object(
                    semantic_graph, "summaries", return_value=mock_summaries
                ):
                    with patch.object(
                        semantic_graph,
                        "extract_facts_from_summaries",
                        AsyncMock(return_value=extracted_facts),
                    ):
                        # Mock cache setitem
                        mock_fact_cache.__setitem__ = Mock()

                        # When: We run main
                        await semantic_graph.main()

                        # Then: Facts should be cached
                        mock_fact_cache.__setitem__.assert_called()

    @pytest.mark.asyncio
    async def test_write_facts_command(self):
        """Test main function with write-facts command"""
        # Given: Command line args for write facts
        with patch("argparse.ArgumentParser.parse_args") as mock_parse:
            mock_args = Mock()
            mock_args.command = "write-facts"
            mock_parse.return_value = mock_args

            with patch("diskcache.Cache") as mock_cache_class:
                mock_extraction_cache = Mock()
                mock_extraction_cache.close = Mock()

                fact_data = Fact(
                    s=Subject(name="test", type="person"),
                    t=Subject(name="org", type="organization"),
                    relationship="works_with",
                )

                mock_fact_cache = Mock()
                mock_fact_cache.close = Mock()
                mock_fact_cache.clear = Mock()
                mock_fact_cache.__iter__ = Mock(return_value=iter(["fact1"]))
                mock_fact_cache.__getitem__ = Mock(return_value=fact_data)

                mock_cache_class.side_effect = [mock_extraction_cache, mock_fact_cache]

                with patch.object(
                    semantic_graph, "update_semantic_graph_with_facts"
                ) as mock_update:
                    # When: We run main
                    await semantic_graph.main()

                    # Then: Facts should be written
                    mock_update.assert_called_once()
                    mock_fact_cache.clear.assert_called_once()


class TestSummariesFunction:
    """Test cases for summaries generator function"""

    def test_summaries_generator(self):
        """Test the summaries generator function"""
        # Given: Mock Summary nodes
        mock_summaries = [
            Mock(summary_text="Summary 1"),
            Mock(summary_text="Summary 2"),
            Mock(summary_text="Summary 3"),
            Mock(summary_text="Summary 4"),
        ]

        MockSummary.nodes.all.return_value = mock_summaries

        # When: We get summaries with offset and limit
        result = list(semantic_graph.summaries(offset=1, n=3))

        # Then: Should return the correct slice
        assert result == ["Summary 2", "Summary 3"]
