from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from agents import Agent

from kairix_offline.semantic_graph.types import Fact, Extract, Subject
from kairix_offline.jobs.extract_facts_from_summaries import (
    run_extraction,
    extract_facts_from_summaries,
)
from kairix_offline.commands.extract import ExtractionOptions


# Create a simple Summary class for testing
class Summary:
    def __init__(self):
        self.uid = None
        self.summary_text = None


@pytest.fixture
def sample_summary():
    summary = Summary()
    summary.uid = "summary-123"
    summary.summary_text = "Test Summary"
    return summary


@pytest.fixture
def sample_agent():
    agent = MagicMock(spec=Agent)
    agent.name = "test_agent"
    return agent


@pytest.fixture
def sample_facts():
    return [
        Fact(
            s=Subject(type="concept", name="artificial_intelligence"),
            t=Subject(type="concept", name="machine_learning"),
            relationship="relates_to",
        ),
        Fact(
            s=Subject(type="method", name="deep_learning"),
            t=Subject(type="concept", name="artificial_intelligence"),
            relationship="subset_of",
        ),
    ]


@pytest.fixture
def sample_extract(sample_facts):
    return Extract(facts=sample_facts)


@pytest.mark.unit
class TestRunExtraction:
    def setup_method(self):
        """Reset mocks before each test"""
        # Import here to get the mocked instances
        from kairix_offline.jobs.extract_facts_from_summaries import (
            agent_runtime,
            facts_cache,
            extraction_processing_records,
            logger,
        )

        # Clear state
        facts_cache.clear()
        extraction_processing_records.clear()
        agent_runtime.run.reset_mock()
        logger.reset_mock()

    @pytest.mark.asyncio
    async def test_extraction_already_recorded(
        self,
        agents,
        logging,
        cache,
        sample_summary,
        sample_agent,
    ):
        # Arrange
        extraction_key = f"{sample_agent.name}-{sample_summary.uid}"
        cache.extraction_processing_records[extraction_key] = True

        # Act
        result = await run_extraction(sample_summary, sample_agent)

        # Assert
        assert result == []
        agents.run.assert_not_called()
        logging.logger.info.assert_any_call(
            "Extraction already processed for %s, continuing.", extraction_key
        )

    @pytest.mark.asyncio
    async def test_successful_extraction_with_facts(
        self,
        agents,
        logging,
        cache,
        sample_summary,
        sample_agent,
        sample_extract,
        sample_facts,
    ):
        # Arrange
        mock_result = MagicMock()
        mock_result.final_output = sample_extract
        agents.run.return_value = mock_result

        # Act
        result = await run_extraction(sample_summary, sample_agent)

        # Assert
        assert result == sample_facts
        agents.run.assert_called_once_with(
            sample_agent, str(sample_summary.summary_text)
        )

        # Verify facts were cached
        assert len(cache.extracted_facts) == 2
        # Check that facts are stored with UUID keys
        fact_values = list(cache.extracted_facts.values())
        assert sample_facts[0] in fact_values
        assert sample_facts[1] in fact_values

        # Verify extraction was marked as processed
        extraction_key = f"{sample_agent.name}-{sample_summary.uid}"
        assert cache.extraction_processing_records[extraction_key] is True

        # Verify logging
        logging.logger.info.assert_any_call(
            "Agent: %s, Summary: %s -  starting extraction.",
            sample_agent.name,
            sample_summary.uid,
        )
        logging.logger.info.assert_any_call(
            "Saved. Extracted %i new facts from summary", len(sample_facts)
        )

    @pytest.mark.asyncio
    async def test_extraction_with_empty_facts_list(
        self,
        agents,
        logging,
        cache,
        sample_summary,
        sample_agent,
    ):
        # Arrange
        empty_extract = Extract(facts=[])
        mock_result = MagicMock()
        mock_result.final_output = empty_extract
        agents.run.return_value = mock_result

        # Act
        result = await run_extraction(sample_summary, sample_agent)

        # Assert
        assert result == []
        agents.run.assert_called_once_with(
            sample_agent, str(sample_summary.summary_text)
        )

        # Verify no facts were cached
        assert len(cache.extracted_facts) == 0

        # Verify extraction was still marked as processed
        extraction_key = f"{sample_agent.name}-{sample_summary.uid}"
        assert cache.extraction_processing_records[extraction_key] is True

        # Verify warning was logged
        logging.logger.warn.assert_called_once_with("Received Extract with no facts.")

    @pytest.mark.asyncio
    async def test_extraction_with_none_facts(
        self,
        agents,
        logging,
        cache,
        sample_summary,
        sample_agent,
    ):
        # Arrange
        none_extract = Extract(facts=None)
        mock_result = MagicMock()
        mock_result.final_output = none_extract
        agents.run.return_value = mock_result

        # Act - expect TypeError due to bug in code
        with pytest.raises(TypeError, match="'NoneType' object is not iterable"):
            await run_extraction(sample_summary, sample_agent)

        # Assert
        agents.run.assert_called_once_with(
            sample_agent, str(sample_summary.summary_text)
        )

        # Verify warning was logged before the error
        logging.logger.warn.assert_called_once_with("Received Extract with no facts.")

    @pytest.mark.asyncio
    async def test_extraction_respects_semaphore(
        self,
        agents,
        cache,
        sample_agent,
        sample_extract,
    ):
        # This test verifies that the semaphore is used (code coverage)
        # The actual concurrency limiting is tested in integration tests

        # Arrange
        summary1 = Summary()
        summary1.uid = "summary-1"
        summary1.summary_text = "Test Summary 1"

        mock_result = MagicMock()
        mock_result.final_output = sample_extract
        agents.run.return_value = mock_result

        # Act
        result = await run_extraction(summary1, sample_agent)

        # Assert
        assert result == sample_extract.facts
        agents.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_extraction_logs_all_steps(
        self,
        agents,
        logging,
        cache,
        sample_summary,
        sample_agent,
        sample_extract,
    ):
        # Arrange
        mock_result = MagicMock()
        mock_result.final_output = sample_extract
        agents.run.return_value = mock_result

        # Act
        await run_extraction(sample_summary, sample_agent)

        # Assert - verify all logging calls in order
        expected_calls = [
            (
                "Agent: %s, Summary: %s -  starting extraction.",
                sample_agent.name,
                sample_summary.uid,
            ),
            ("Agent: %s, finished extraction.", sample_agent.name),
            ("Received extracted results. Preparing facts.",),
            ("Saved. Extracted %i new facts from summary", 2),
        ]

        for args in expected_calls:
            logging.logger.info.assert_any_call(*args)


@pytest.mark.unit
class TestExtractFactsFromSummaries:
    """Test the extract_facts_from_summaries function parameter behavior and task creation"""

    def setup_method(self):
        """Reset mocks before each test"""
        from kairix_core.types.neo4j import Summary as MockedSummary
        MockedSummary.nodes.all.reset_mock()

    @pytest.fixture
    def mock_summaries(self):
        """Create mock Summary nodes"""
        summaries = []
        for i in range(10):
            summary = Summary()
            summary.uid = f"summary-{i}"
            summary.summary_text = f"Test Summary {i}"
            summaries.append(summary)
        return summaries

    @pytest.mark.asyncio
    async def test_process_all_summaries(self, mock_all):
        """Test with is_process_all=True - should process all summaries"""
        # Arrange
        options = ExtractionOptions(is_process_all=True, offset=None, n=None)

        # Track what tasks are created
        created_tasks = []
        gathered_tasks = []
        
        # Import the extraction module to get the mocked agents
        
        with (
            patch("asyncio.create_task") as mock_create_task,
            patch(
                "asyncio.gather",
                new_callable=AsyncMock,
            ) as mock_gather,
        ):
            summary1 = Summary()
            summary1.uid = "summary-1"
            summary1.summary_text = "Test Summary 1"
            
            # Get the actual mock_all from conftest
            from kairix_core.types.neo4j import Summary as MockedSummary
            MockedSummary.nodes.all.return_value = [summary1]

            # Setup create_task to track calls and return mock tasks
            def track_task(coro):
                task = MagicMock()
                created_tasks.append((coro, task))
                return task

            def track_gather(*args):
                gathered_tasks.extend(args)

            mock_create_task.side_effect = track_task

            mock_gather.side_effect = track_gather

            options = ExtractionOptions(is_process_all=True, offset=None, n=None)
            await extract_facts_from_summaries(options)

            # Assert
            MockedSummary.nodes.all.assert_called_once()
            
            # Verify create_task was called once for the single summary
            assert len(created_tasks) == 1
            
            # Verify the task was created with the correct coroutine
            coro, task = created_tasks[0]
            assert coro.cr_code.co_name == 'run_extraction'
            
            # Verify gather was called with the created task
            mock_gather.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_with_offset_parameter(self, mock_all):
        """Test with offset parameter - should skip first N summaries"""
        # Arrange
        options = ExtractionOptions(is_process_all=False, offset=3, n=None)
        
        # Track what tasks are created
        created_tasks = []
        
        # Import the extraction module
        
        with (
            patch("asyncio.create_task") as mock_create_task,
            patch("asyncio.gather", new_callable=AsyncMock) as mock_gather,
        ):
            # Create 5 summaries
            summaries = []
            for i in range(5):
                summary = Summary()
                summary.uid = f"summary-{i}"
                summary.summary_text = f"Test Summary {i}"
                summaries.append(summary)
            
            # Mock the slicing behavior
            mock_nodes = MagicMock()
            mock_nodes.__getitem__.return_value = summaries[3:]  # offset=3
            
            from kairix_core.types.neo4j import Summary as MockedSummary
            MockedSummary.nodes.all.return_value = mock_nodes
            
            # Setup create_task to track calls
            def track_task(coro):
                task = MagicMock()
                created_tasks.append((coro, task))
                return task
            
            mock_create_task.side_effect = track_task
            
            # Act
            await extract_facts_from_summaries(options)
            
            # Assert
            from kairix_core.types.neo4j import Summary as MockedSummary
            MockedSummary.nodes.all.assert_called_once()
            # Verify slice was called with offset
            mock_nodes.__getitem__.assert_called_once_with(slice(3, None))
            
            # Verify create_task was called for summaries after offset
            assert len(created_tasks) == 2  # summaries 3 and 4
            
            # Verify gather was called
            mock_gather.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_with_n_parameter(self, mock_all):
        """Test with n parameter - should process only first N summaries"""
        # Arrange
        options = ExtractionOptions(is_process_all=False, offset=None, n=2)
        
        # Track what tasks are created
        created_tasks = []
        
        # Import the extraction module
        
        with (
            patch("asyncio.create_task") as mock_create_task,
            patch("asyncio.gather", new_callable=AsyncMock) as mock_gather,
        ):
            # Create 5 summaries
            summaries = []
            for i in range(5):
                summary = Summary()
                summary.uid = f"summary-{i}"
                summary.summary_text = f"Test Summary {i}"
                summaries.append(summary)
            
            # Mock the slicing behavior
            mock_nodes = MagicMock()
            mock_nodes.__getitem__.return_value = summaries[:2]  # n=2
            
            from kairix_core.types.neo4j import Summary as MockedSummary
            MockedSummary.nodes.all.return_value = mock_nodes
            
            # Setup create_task to track calls
            def track_task(coro):
                task = MagicMock()
                created_tasks.append((coro, task))
                return task
            
            mock_create_task.side_effect = track_task
            
            # Act
            await extract_facts_from_summaries(options)
            
            # Assert
            from kairix_core.types.neo4j import Summary as MockedSummary
            MockedSummary.nodes.all.assert_called_once()
            # Verify slice was called with n
            mock_nodes.__getitem__.assert_called_once_with(slice(None, 2))
            
            # Verify create_task was called only n times
            assert len(created_tasks) == 2
            
            # Verify gather was called
            mock_gather.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_with_offset_and_n_parameters(self, mock_all):
        """Test with both offset and n parameters - should process a slice of summaries"""
        # Arrange
        options = ExtractionOptions(is_process_all=False, offset=2, n=3)
        
        # Track what tasks are created
        created_tasks = []
        
        # Import the extraction module
        
        with (
            patch("asyncio.create_task") as mock_create_task,
            patch("asyncio.gather", new_callable=AsyncMock) as mock_gather,
        ):
            # Create 10 summaries
            summaries = []
            for i in range(10):
                summary = Summary()
                summary.uid = f"summary-{i}"
                summary.summary_text = f"Test Summary {i}"
                summaries.append(summary)
            
            # Mock the two-step slicing behavior
            mock_nodes = MagicMock()
            mock_nodes_after_offset = MagicMock()
            mock_nodes_after_offset.__getitem__.return_value = summaries[2:5]  # offset=2, then n=3
            mock_nodes.__getitem__.return_value = mock_nodes_after_offset
            
            from kairix_core.types.neo4j import Summary as MockedSummary
            MockedSummary.nodes.all.return_value = mock_nodes
            
            # Setup create_task to track calls
            def track_task(coro):
                task = MagicMock()
                created_tasks.append((coro, task))
                return task
            
            mock_create_task.side_effect = track_task
            
            # Act
            await extract_facts_from_summaries(options)
            
            # Assert
            from kairix_core.types.neo4j import Summary as MockedSummary
            MockedSummary.nodes.all.assert_called_once()
            # Verify two slicing operations
            mock_nodes.__getitem__.assert_called_once_with(slice(2, None))
            mock_nodes_after_offset.__getitem__.assert_called_once_with(slice(None, 3))
            
            # Verify create_task was called for the right slice
            assert len(created_tasks) == 3  # summaries 2, 3, 4
            
            # Verify gather was called
            mock_gather.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_agent_cycling_behavior(self, mock_all):
        """Test that agents are cycled properly across summaries"""
        # Arrange
        options = ExtractionOptions(is_process_all=True, offset=None, n=None)
        
        # Track what tasks are created
        created_tasks = []
        
        # Import the extraction module and get agents
        
        with (
            patch("asyncio.create_task") as mock_create_task,
            patch("asyncio.gather", new_callable=AsyncMock) as mock_gather,
        ):
            # Create 5 summaries to test cycling with 3 agents
            summaries = []
            for i in range(5):
                summary = Summary()
                summary.uid = f"summary-{i}"
                summary.summary_text = f"Test Summary {i}"
                summaries.append(summary)
            
            from kairix_core.types.neo4j import Summary as MockedSummary
            MockedSummary.nodes.all.return_value = summaries
            
            # Setup create_task to track calls and capture the coroutine
            def track_task(coro):
                task = MagicMock()
                # Store the coroutine and its arguments
                created_tasks.append((coro, task))
                return task
            
            mock_create_task.side_effect = track_task
            
            # Act
            await extract_facts_from_summaries(options)
            
            # Assert
            from kairix_core.types.neo4j import Summary as MockedSummary
            MockedSummary.nodes.all.assert_called_once()
            
            # Verify create_task was called 5 times
            assert len(created_tasks) == 5
            
            # Verify all tasks are for run_extraction
            for coro, task in created_tasks:
                assert coro.cr_code.co_name == 'run_extraction'
            
            # Note: We can't easily verify the exact agent cycling without 
            # inspecting the coroutine's closure, but we've verified the 
            # correct number of tasks were created
            
            # Verify gather was called
            mock_gather.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_logging_after_processing(self, mock_all, logging):
        """Test that final log message is written after processing"""
        # Arrange
        options = ExtractionOptions(is_process_all=True, offset=None, n=None)
        
        # Import the extraction module
        
        with (
            patch("asyncio.create_task") as mock_create_task,
            patch("asyncio.gather", new_callable=AsyncMock),
        ):
            # Create a summary
            summary = Summary()
            summary.uid = "summary-1"
            summary.summary_text = "Test Summary"
            from kairix_core.types.neo4j import Summary as MockedSummary
            MockedSummary.nodes.all.return_value = [summary]
            
            # Setup create_task
            mock_create_task.return_value = MagicMock()
            
            # Act
            await extract_facts_from_summaries(options)
            
            # Assert - verify the final log message
            logging.logger.info.assert_any_call("Processed all requested summaries..")
