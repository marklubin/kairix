"""
Mock tests for entity discussions that don't require API access.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from cognition_engine.configuration.runner import (
    CognitionAgentRunner
)
from agents import RunResult

from tests.test_entity_discussion_with_grading import (
    EntityConversationSystem,
    ConversationScenario,
    DialogueCritique,
    get_test_scenarios
)


class TestEntityDiscussionsMocked:
    """Test entity discussions with mocked responses"""
    
    @pytest.fixture
    def mock_runner(self):
        """Create a mock runner that simulates responses"""
        runner = Mock(spec=CognitionAgentRunner)
        
        # Response patterns for different agents
        alice_responses = [
            "Oh, that brings back such wonderful memories! How have you been?",
            "I've been exploring so many creative projects lately. The journey matters more than the destination, don't you think?",
            "That resonates deeply with me. There's something beautiful about how technology can enhance human connection.",
            "Your analytical approach complements my intuitive one perfectly!",
            "I love how we see things from different angles. It makes our conversations so rich."
        ]
        
        bob_responses = [
            "It's been quite productive! I've been working on optimizing several systems.",
            "That's an interesting perspective. From a practical standpoint, I'd suggest we focus on measurable outcomes.",
            "Let me analyze the key components: efficiency, scalability, and user experience.",
            "Based on the data, I think we should prioritize the technical implementation first.",
            "I've created a list of action items we should consider moving forward."
        ]
        
        grader_critique = DialogueCritique(
            personality_consistency=8.5,
            natural_flow=8.0,
            theme_coverage=7.5,
            overall_quality=8.0,
            average_score=8.0,
            strengths=["Clear personality distinction", "Natural conversation flow"],
            weaknesses=["Could explore themes more deeply"],
            detailed_feedback="The dialogue shows good personality consistency with Alice being creative and Bob being analytical."
        )
        
        async def mock_run(agent, stimulus):
            result = Mock(spec=RunResult)
            
            # Determine response based on agent name
            if "alice" in agent.name:
                response = alice_responses[hash(stimulus) % len(alice_responses)]
            elif "bob" in agent.name:
                response = bob_responses[hash(stimulus) % len(bob_responses)]
            elif "grader" in agent.name:
                # Return the critique object
                result.final_output_as = Mock(return_value=grader_critique)
                return result
            else:
                response = "Default response"
            
            result.final_output_as = Mock(return_value=response)
            return result
        
        runner.run = AsyncMock(side_effect=mock_run)
        return runner
    
    @pytest.mark.asyncio
    async def test_conversation_flow(self, mock_runner):
        """Test basic conversation flow with mocked responses"""
        system = EntityConversationSystem(mock_runner)
        
        scenario = ConversationScenario(
            name="Test Scenario",
            description="Testing conversation flow",
            initial_message="Hello! How are you?",
            expected_themes=["greeting", "conversation"],
            max_turns=4
        )
        
        dialogue = await system.run_conversation(scenario)
        
        # Verify dialogue structure
        assert len(dialogue) == 4
        assert dialogue[0].speaker == "Alice"
        assert dialogue[1].speaker == "Bob"
        assert dialogue[2].speaker == "Alice"
        assert dialogue[3].speaker == "Bob"
        
        # Verify responses contain expected patterns
        alice_turns = [turn for turn in dialogue if turn.speaker == "Alice"]
        bob_turns = [turn for turn in dialogue if turn.speaker == "Bob"]
        
        # Alice should be more emotive/creative
        assert any(any(word in turn.message.lower() for word in ["wonderful", "beautiful", "resonates", "love"])
                  for turn in alice_turns)
        
        # Bob should be more analytical
        assert any(any(word in turn.message.lower() for word in ["data", "analyze", "practical", "optimize", "list"])
                  for turn in bob_turns)
    
    @pytest.mark.asyncio
    async def test_grading_system(self, mock_runner):
        """Test the grading system with mocked responses"""
        system = EntityConversationSystem(mock_runner)
        
        scenario = ConversationScenario(
            name="Grading Test",
            description="Test grading functionality",
            initial_message="Let's discuss our project",
            expected_themes=["collaboration", "planning"],
            max_turns=2
        )
        
        # Run conversation
        dialogue = await system.run_conversation(scenario)
        
        # Grade it
        critique = await system.grade_conversation(scenario, dialogue)
        
        # Verify critique structure
        assert isinstance(critique, DialogueCritique)
        assert critique.personality_consistency == 8.5
        assert critique.natural_flow == 8.0
        assert critique.theme_coverage == 7.5
        assert critique.overall_quality == 8.0
        assert critique.average_score == 8.0
        assert len(critique.strengths) > 0
        assert len(critique.weaknesses) > 0
        assert len(critique.detailed_feedback) > 0
        
        # Should pass threshold
        assert critique.average_score >= 7.0
    
    @pytest.mark.asyncio
    async def test_memory_accumulation(self, mock_runner):
        """Test that memories accumulate during conversation"""
        system = EntityConversationSystem(mock_runner)
        
        # Initially empty
        assert len(system.alice_memory.memories) == 0
        assert len(system.bob_memory.memories) == 0
        
        scenario = ConversationScenario(
            name="Memory Test",
            description="Testing memory accumulation",
            initial_message="Tell me about your day",
            expected_themes=["daily activities"],
            max_turns=2
        )
        
        await system.run_conversation(scenario)
        
        # Should have memories now (2 per turn: what they heard + their response)
        assert len(system.alice_memory.memories) >= 2
        assert len(system.bob_memory.memories) >= 2
        
        # Check memory content
        alice_memories = [m.content for m in system.alice_memory.memories]
        assert any("They said:" in m for m in alice_memories)
        assert any("I responded:" in m for m in alice_memories)
    
    def test_scenario_definitions(self):
        """Test that all scenarios are properly defined"""
        scenarios = get_test_scenarios()
        
        assert len(scenarios) == 5
        
        for scenario in scenarios:
            assert scenario.name
            assert scenario.description
            assert scenario.initial_message
            assert len(scenario.expected_themes) > 0
            assert scenario.max_turns > 0
            
        # Check specific scenarios exist
        scenario_names = [s.name for s in scenarios]
        assert "Coffee Shop Reunion" in scenario_names
        assert "Project Planning" in scenario_names
        assert "Philosophy Discussion" in scenario_names
    
    @pytest.mark.asyncio
    async def test_passing_threshold_logic(self, mock_runner):
        """Test the pass/fail logic"""
        system = EntityConversationSystem(mock_runner)
        
        # Create a scenario that should pass
        scenario = ConversationScenario(
            name="Pass Test",
            description="Should pass grading",
            initial_message="Hello",
            expected_themes=["greeting"],
            max_turns=2
        )
        
        dialogue = await system.run_conversation(scenario)
        critique = await system.grade_conversation(scenario, dialogue)
        
        # With mocked score of 8.0, should pass 7.0 threshold
        THRESHOLD = 7.0
        assert critique.average_score >= THRESHOLD
        
        # Test the logic
        passed = critique.average_score >= THRESHOLD
        assert passed is True