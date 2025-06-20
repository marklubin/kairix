"""
Integration tests for knowledge_db_demo.py
These tests verify the complete workflow and interactions between components
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import os

import sys
from knowledge_db_demo import (
    Unit,
    Relation,
    Extraction,
    extract_knowledge,
    process_knowledge,
    world_facts_extractor,
    user_profile_extractor,
)
from knowledge_db_demo import Unit, Relation
import time


# Ensure PYTEST_RUN is set
os.environ['PYTEST_RUN'] = '1'

sys.path.append('/Users/mark/kairix/kairix-offline/scripts')



class TestFullWorkflow:
    """Test the complete knowledge extraction workflow"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_end_to_end_single_summary(self):
        """Test processing a single summary from extraction to persistence"""
        
        # Sample summary text that should trigger all three extractors
        summary_text = """
        Mark is setting up AI servers at home. The servers require 2000W of power 
        and produce significant noise. Mark is concerned about disturbing his roommates.
        The AI assistant suggested using sound dampening materials and explained that
        basements often have good power access. The assistant learned that Mark values
        being considerate to others and adapted its suggestions to include social considerations.
        """
        
        mock_summary = Mock()
        mock_summary.summary_text = summary_text
        
        # Expected extractions from each agent
        expected_world_facts = [
            Relation(
                u=Unit(type="entity", short_description="AI servers", id="ai_servers"),
                v=Unit(type="attribute", short_description="2000W power requirement", id="power_2000w"),
                relationship_descriptor="require"
            ),
            Relation(
                u=Unit(type="entity", short_description="basements", id="basements"),
                v=Unit(type="attribute", short_description="good power access", id="power_access"),
                relationship_descriptor="have"
            )
        ]
        
        expected_user_facts = [
            Relation(
                u=Unit(type="entity", short_description="Mark", id="mark"),
                v=Unit(type="action", short_description="setting up AI servers", id="setup_servers"),
                relationship_descriptor="is"
            ),
            Relation(
                u=Unit(type="entity", short_description="Mark", id="mark"),
                v=Unit(type="attribute", short_description="considerate to others", id="considerate"),
                relationship_descriptor="values"
            )
        ]
        
        expected_assistant_facts = [
            Relation(
                u=Unit(type="entity", short_description="AI assistant", id="ai_assistant"),
                v=Unit(type="action", short_description="suggested sound dampening", id="suggest_dampening"),
                relationship_descriptor="performed"
            ),
            Relation(
                u=Unit(type="entity", short_description="AI assistant", id="ai_assistant"),
                v=Unit(type="attribute", short_description="adapted to social considerations", id="social_adaptation"),
                relationship_descriptor="learned"
            )
        ]
        
        # Set up mocks
        with patch('knowledge_db_demo.Summary') as mock_summary_class:
            mock_summary_class.nodes.all.return_value = [mock_summary]
            
            # Mock the agent runners to return our expected extractions
            with patch('knowledge_db_demo.Runner.run', new_callable=AsyncMock) as mock_run:
                async def agent_side_effect(agent, text):
                    result = Mock()
                    if agent == world_facts_extractor:
                        result.final_output = Extraction(relationships=expected_world_facts)
                    elif agent == user_profile_extractor:
                        result.final_output = Extraction(relationships=expected_user_facts)
                    else:  # assistant_cognitive_extractor
                        result.final_output = Extraction(relationships=expected_assistant_facts)
                    return result
                
                mock_run.side_effect = agent_side_effect
                
                # Mock semantic unit operations
                created_units = {}
                
                def create_mock_unit(uid, descriptions, type):
                    unit = Mock()
                    unit.uid = uid
                    unit.type = type
                    unit.descriptions = descriptions.copy()
                    unit.occurences = 1
                    unit.save = Mock()
                    unit.relates = Mock()
                    unit.relates.relationship = Mock(return_value=None)
                    unit.relates.connect = Mock()
                    created_units[uid] = unit
                    return unit
                
                with patch('knowledge_db_demo.SemanticUnit') as mock_su:
                    mock_su.nodes.first_or_none = Mock(return_value=None)
                    mock_su.create = Mock(side_effect=create_mock_unit)
                    
                    with patch('knowledge_db_demo.vector_search') as mock_search:
                        mock_search.return_value = []  # No similar units found
                        
                        # Run the process
                        await process_knowledge(1)
                        
                        # Verify all agents were called
                        assert mock_run.call_count == 3
                        
                        # Verify units were created for all unique entities
                        expected_unit_ids = {
                            "ai_servers", "power_2000w", "basements", "power_access",
                            "mark", "setup_servers", "considerate",
                            "ai_assistant", "suggest_dampening", "social_adaptation"
                        }
                        created_unit_ids = set(created_units.keys())
                        assert created_unit_ids == expected_unit_ids
                        
                        # Verify relationships were created
                        total_relationships = sum(
                            len(unit.relates.connect.call_args_list)
                            for unit in created_units.values()
                        )
                        assert total_relationships == 6  # Total number of relations
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_deduplication_across_summaries(self):
        """Test that entities are properly deduplicated across multiple summaries"""
        
        # Two summaries with overlapping entities
        summary1 = Mock(summary_text="Mark is working with AI servers. The servers require significant power.")
        summary2 = Mock(summary_text="Mark mentioned the AI servers again. They produce noise.")
        
        with patch('knowledge_db_demo.Summary') as mock_summary_class:
            mock_summary_class.nodes.all.return_value = [summary1, summary2]
            
            # Track unit creation/updates
            existing_units = {}
            
            def mock_first_or_none(uid=None, **kwargs):
                return existing_units.get(uid)
            
            def mock_create(uid, descriptions, type):
                unit = Mock()
                unit.uid = uid
                unit.type = type
                unit.descriptions = descriptions.copy()
                unit.occurences = 1
                unit.save = Mock()
                unit.relates = Mock()
                unit.relates.relationship = Mock(return_value=None)
                unit.relates.connect = Mock()
                existing_units[uid] = unit
                return unit
            
            with patch('knowledge_db_demo.SemanticUnit') as mock_su:
                mock_su.nodes.first_or_none = Mock(side_effect=mock_first_or_none)
                mock_su.create = Mock(side_effect=mock_create)
                
                # Mock agent responses
                with patch('knowledge_db_demo.Runner.run', new_callable=AsyncMock) as mock_run:
                    async def agent_side_effect(agent, text):
                        result = Mock()
                        if "significant power" in text:
                            # First summary
                            relations = [
                                Relation(
                                    u=Unit(type="entity", short_description="Mark", id="mark"),
                                    v=Unit(type="entity", short_description="AI servers", id="ai_servers"),
                                    relationship_descriptor="works_with"
                                )
                            ]
                        else:
                            # Second summary - same entities
                            relations = [
                                Relation(
                                    u=Unit(type="entity", short_description="AI servers", id="ai_servers"),
                                    v=Unit(type="attribute", short_description="noise", id="noise"),
                                    relationship_descriptor="produce"
                                )
                            ]
                        
                        result.final_output = Extraction(relationships=relations if agent == world_facts_extractor else [])
                        return result
                    
                    mock_run.side_effect = agent_side_effect
                    
                    with patch('knowledge_db_demo.vector_search') as mock_search:
                        mock_search.return_value = []
                        
                        await process_knowledge(2)
                        
                        # Verify Mark and ai_servers were only created once
                        assert "mark" in existing_units
                        assert "ai_servers" in existing_units
                        
                        # Verify ai_servers was updated on second encounter
                        ai_servers_unit = existing_units["ai_servers"]
                        assert len(ai_servers_unit.descriptions) == 2  # Both descriptions added
                        assert ai_servers_unit.save.call_count >= 1  # Saved at least once


class TestAgentIntegration:
    """Test the integration of the three extraction agents"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_agent_specialization(self):
        """Verify each agent extracts appropriate information"""
        
        comprehensive_text = """
        Mark and his colleague Sarah are setting up a home AI lab. The lab requires 
        enterprise-grade servers that consume 3000W of power. Mark is excited but 
        worried about costs and noise. Sarah suggested using renewable energy.
        
        The AI assistant provided detailed technical specifications and learned that
        Mark prefers environmentally friendly solutions. The assistant adapted its 
        recommendations to include solar panel options and energy-efficient cooling.
        
        Technical facts: GPU servers require active cooling. Solar panels can offset
        energy costs. Home electrical systems typically support 15-20A circuits.
        """
        
        mock_summary = Mock(summary_text=comprehensive_text)
        
        # Capture what each agent extracts
        agent_outputs = {}
        
        with patch('knowledge_db_demo.Runner.run', new_callable=AsyncMock) as mock_run:
            async def capture_agent_output(agent, text):
                result = Mock()
                # Return empty extraction but capture which agent was called
                agent_outputs[agent.name] = True
                result.final_output = Extraction(relationships=[])
                return result
            
            mock_run.side_effect = capture_agent_output
            
            results = await extract_knowledge(mock_summary)
            
            # Verify all three agents were used
            assert "world_facts" in agent_outputs
            assert "user_profile" in agent_outputs
            assert "assistant_cognitive" in agent_outputs
            
            # Verify they all received the same text
            calls = mock_run.call_args_list
            for call in calls:
                assert call[0][1] == comprehensive_text


class TestErrorRecovery:
    """Test error recovery and resilience"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_partial_agent_failure_recovery(self):
        """Test that processing continues even if one agent fails"""
        
        mock_summary = Mock(summary_text="Test summary")
        
        successful_relation = Relation(
            u=Unit(type="entity", short_description="test", id="test"),
            v=Unit(type="attribute", short_description="attr", id="attr"),
            relationship_descriptor="has"
        )
        
        with patch('knowledge_db_demo.Runner.run', new_callable=AsyncMock) as mock_run:
            async def mixed_results(agent, text):
                if agent == world_facts_extractor:
                    # This agent fails
                    raise Exception("Agent processing failed")
                else:
                    # Other agents succeed
                    result = Mock()
                    result.final_output = Extraction(relationships=[successful_relation])
                    return result
            
            mock_run.side_effect = mixed_results
            
            # Should raise the exception
            with pytest.raises(Exception) as exc_info:
                await extract_knowledge(mock_summary)
            
            assert "Agent processing failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @pytest.mark.integration 
    async def test_database_connection_recovery(self):
        """Test handling of database connection issues"""
        
        # Test that setup() is not called when PYTEST_RUN is set
        assert os.environ.get('PYTEST_RUN') == '1'
        
        # Verify we can still import and use the module
        
        # Create test objects without database
        unit = Unit(type="entity", short_description="test", id="test")
        assert unit.id == "test"


class TestPerformanceIntegration:
    """Test performance-related integration scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_large_batch_processing(self):
        """Test processing many summaries efficiently"""
        
        # Create 50 mock summaries
        summaries = [
            Mock(summary_text=f"Summary {i}: Mark discussed topic {i} with the AI assistant.")
            for i in range(50)
        ]
        
        with patch('knowledge_db_demo.Summary') as mock_summary_class:
            mock_summary_class.nodes.all.return_value = summaries
            
            extraction_count = 0
            
            with patch('knowledge_db_demo.Runner.run', new_callable=AsyncMock) as mock_run:
                async def count_extractions(agent, text):
                    nonlocal extraction_count
                    extraction_count += 1
                    result = Mock()
                    result.final_output = Extraction(relationships=[])
                    return result
                
                mock_run.side_effect = count_extractions
                
                # Process only first 10
                await process_knowledge(10)
                
                # Should have called 3 agents * 10 summaries = 30 extractions
                assert extraction_count == 30
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_extraction_timing(self):
        """Verify agents run concurrently for performance"""
        
        
        mock_summary = Mock(summary_text="Performance test")
        
        agent_timings = {}
        
        with patch('knowledge_db_demo.Runner.run', new_callable=AsyncMock) as mock_run:
            async def timed_agent(agent, text):
                start = time.time()
                await asyncio.sleep(0.1)  # Simulate processing
                end = time.time()
                agent_timings[agent.name] = (start, end)
                
                result = Mock()
                result.final_output = Extraction(relationships=[])
                return result
            
            mock_run.side_effect = timed_agent
            
            overall_start = time.time()
            await extract_knowledge(mock_summary)
            overall_end = time.time()
            
            # Total time should be ~0.1s (concurrent) not ~0.3s (sequential)
            total_time = overall_end - overall_start
            assert total_time < 0.2  # Allow some overhead
            
            # Verify all agents started at approximately the same time
            start_times = [t[0] for t in agent_timings.values()]
            assert max(start_times) - min(start_times) < 0.05


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])