#!/usr/bin/env python3
"""
Functional test for SummaryInsightPerceptor to debug k=0 FAISS error
Run with: pytest -xvs tests/test_insight_perceptor_functional.py -m insight_debug
"""

import pytest
import os
import asyncio
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.cognition.perceptor.summary_insight import SummaryInsightPerceptor
from kairix_core.cognition.stores.sqlite_embedded_data import SQLiteEmbeddedDataStore
from kairix_core.types.environmental_context import PersonaEnvironment
from kairix_core.types.cognition import StimulusType, Perception, Stimulus

# Set up logging
logger = LoggingRuntime().logger

@pytest.mark.insight_debug
class TestSummaryInsightPerceptor:
    """Test the SummaryInsightPerceptor with real database"""
    
    @pytest.fixture
    def db_path(self):
        """Get the actual database path"""
        db_path = os.path.expanduser("~/.sqlite/kairix.db")
        assert os.path.exists(db_path), f"Database not found at {db_path}"
        return db_path
    
    @pytest.fixture
    def runtime(self):
        """Create runtime"""
        from kairix_core.runtime.agent import AgentRuntime
        return AgentRuntime()
    
    @pytest.fixture
    def embedded_store(self, db_path):
        """Create embedded data store"""
        # Override the database path
        os.environ["KAIRIX_SQLITE_VSS_PATH"] = db_path
        return SQLiteEmbeddedDataStore()
    
    @pytest.fixture
    async def perceptor(self, runtime, embedded_store):
        """Create the perceptor"""
        # Check environment variable
        n_summaries_str = os.getenv("KAIRIX_N_SUMMARIES_PER_MESSAGE", "20")
        k_memories = int(n_summaries_str)
        logger.info(f"Creating perceptor with k_memories={k_memories}")
        
        perceptor = SummaryInsightPerceptor(
            runtime=runtime,
            embedded_sumary_store=embedded_store,
            k_memories=k_memories  # Explicitly set from env or default
        )
        return perceptor
    
    @pytest.mark.asyncio
    async def test_basic_perception(self, perceptor):
        """Test basic perception without crashing"""
        logger.info("Starting basic perception test")
        
        # Create a simple stimulus
        stimulus = Stimulus(
            stimulus_type=StimulusType.user_message,
            content="Hello, this is a test message",
            metadata={}
        )
        
        logger.info(f"Created stimulus: {stimulus}")
        
        try:
            # Test if we can perceive
            perception = await perceptor.perceive(stimulus)
            logger.info(f"Perception result: {perception}")
            assert perception is not None
            
        except Exception as e:
            logger.error(f"Error during perception: {e}", exc_info=True)
            raise
    
    @pytest.mark.asyncio
    async def test_empty_keywords(self, perceptor):
        """Test with empty keywords to see if that causes k=0"""
        logger.info("Testing empty keywords scenario")
        
        stimulus = Stimulus(
            stimulus_type=StimulusType.user_message,
            content="",  # Empty content
            metadata={}
        )
        
        try:
            perception = await perceptor.perceive(stimulus)
            logger.info(f"Empty keyword perception: {perception}")
            
        except Exception as e:
            logger.error(f"Error with empty keywords: {e}", exc_info=True)
            raise
    
    @pytest.mark.asyncio 
    async def test_direct_gather_memories(self, perceptor):
        """Test the gather_memories method directly"""
        logger.info("Testing gather_memories directly")
        
        # Test with some keywords
        keywords = ["test", "hello", "world"]
        
        try:
            # Call the method that's failing
            memories = await perceptor._gather_memories(keywords)
            logger.info(f"Got {len(memories)} memories")
            
        except Exception as e:
            logger.error(f"Error gathering memories: {e}", exc_info=True)
            raise
    
    @pytest.mark.asyncio
    async def test_k_memories_value(self, perceptor):
        """Check the actual k_memories value"""
        logger.info(f"Perceptor k_memories value: {perceptor.k_memories}")
        logger.info(f"Perceptor type: {type(perceptor.k_memories)}")
        
        # Also check environment variable
        env_value = os.getenv("KAIRIX_N_SUMMARIES_PER_MESSAGE")
        logger.info(f"KAIRIX_N_SUMMARIES_PER_MESSAGE env var: {env_value}")
        
        assert perceptor.k_memories > 0, f"k_memories is {perceptor.k_memories}, should be > 0"


if __name__ == "__main__":
    # Run the test
    pytest.main([__file__, "-xvs", "-m", "insight_debug"])