"""
Simplified test for entity discussions that doesn't require O3 API.
Tests basic conversation flow between two entities.
"""

import pytest
from typing import List
from unittest.mock import Mock, AsyncMock

from cognition_engine import (
    Stimulus, 
    StimulusType,
    Perception,
    Perceptor
)
from cognition_engine.configuration.runner import (
    CognitionAgentRunner
)
from agents import Agent as OpenAIAgent, RunResult


class SimpleMemoryStore:
    """Simple in-memory store for testing"""
    def __init__(self, entity_name: str):
        self.entity_name = entity_name
        self.memories = []
    
    def add(self, content: str):
        self.memories.append(content)
    
    def search(self, query: str, k: int = 3) -> List[str]:
        # Return last k memories
        return self.memories[-k:] if self.memories else []


class TestEntityDiscussion:
    """Test basic entity discussion functionality"""
    
    @pytest.fixture
    def mock_runner(self):
        """Create a mock runner for testing"""
        runner = Mock(spec=CognitionAgentRunner)
        
        async def mock_run(agent, stimulus):
            # Generate different responses based on agent name/personality
            result = Mock(spec=RunResult)
            
            if "warm and empathetic" in agent.instructions:
                # Alice's style
                responses = [
                    "Oh, how wonderful to hear from you! Tell me more.",
                    "That's fascinating! I've been thinking about similar things.",
                    "Your perspective really resonates with me.",
                    "I love how you put that into words!"
                ]
            else:
                # Bob's style  
                responses = [
                    "That's an interesting point. Let me analyze that.",
                    "Based on the data, I would suggest we consider this approach.",
                    "I've made a list of key points we should discuss.",
                    "The logical next step would be to examine the facts."
                ]
            
            # Cycle through responses
            response_idx = hash(stimulus) % len(responses)
            result.final_output_as = Mock(return_value=responses[response_idx])
            return result
        
        runner.run = AsyncMock(side_effect=mock_run)
        return runner
    
    @pytest.fixture
    def alice_perceptor(self):
        """Create Alice's perceptor"""
        memory_store = SimpleMemoryStore("Alice")
        
        class AlicePerceptor(Perceptor):
            async def perceive(self, stimulus: Stimulus) -> List[Perception]:
                if stimulus.type == StimulusType.user_message:
                    memory_store.add(stimulus.content)
                    memories = memory_store.search(stimulus.content)
                    
                    perceptions = [
                        Perception(
                            content=stimulus.content,
                            source="current_input",
                            confidence=1.0
                        )
                    ]
                    
                    for memory in memories:
                        perceptions.append(Perception(
                            content=f"I remember: {memory}",
                            source="alice_memory",
                            confidence=0.8
                        ))
                    
                    return perceptions
                return []
        
        return AlicePerceptor()
    
    @pytest.fixture
    def bob_perceptor(self):
        """Create Bob's perceptor"""
        memory_store = SimpleMemoryStore("Bob")
        
        class BobPerceptor(Perceptor):
            async def perceive(self, stimulus: Stimulus) -> List[Perception]:
                if stimulus.type == StimulusType.user_message:
                    memory_store.add(stimulus.content)
                    memories = memory_store.search(stimulus.content)
                    
                    perceptions = [
                        Perception(
                            content=stimulus.content,
                            source="current_input",
                            confidence=1.0
                        )
                    ]
                    
                    for memory in memories:
                        perceptions.append(Perception(
                            content=f"Data point: {memory}",
                            source="bob_memory",
                            confidence=0.9
                        ))
                    
                    return perceptions
                return []
        
        return BobPerceptor()
    
    @pytest.mark.asyncio
    async def test_basic_conversation_flow(self, mock_runner, alice_perceptor, bob_perceptor):
        """Test basic conversation between two entities"""
        dialogue = []
        
        # Initial message
        initial_stimulus = Stimulus(
            content="Hello! How are you today?",
            type=StimulusType.user_message
        )
        
        # Alice perceives and responds
        alice_perceptions = await alice_perceptor.perceive(initial_stimulus)
        assert len(alice_perceptions) >= 1
        assert alice_perceptions[0].content == "Hello! How are you today?"
        
        # Generate Alice's response
        alice_agent = OpenAIAgent(
            name="alice",
            instructions="You are Alice with a warm and empathetic personality."
        )
        alice_result = await mock_runner.run(alice_agent, initial_stimulus.content)
        alice_response = alice_result.final_output_as()
        
        dialogue.append(("Alice", alice_response))
        assert any(word in alice_response.lower() for word in ["wonderful", "fascinating", "resonates", "love"])
        
        # Bob perceives Alice's response
        bob_stimulus = Stimulus(
            content=alice_response,
            type=StimulusType.user_message
        )
        bob_perceptions = await bob_perceptor.perceive(bob_stimulus)
        assert len(bob_perceptions) >= 1
        
        # Generate Bob's response
        bob_agent = OpenAIAgent(
            name="bob",
            instructions="You are Bob with a logical and analytical personality."
        )
        bob_result = await mock_runner.run(bob_agent, alice_response)
        bob_response = bob_result.final_output_as()
        
        dialogue.append(("Bob", bob_response))
        assert any(word in bob_response.lower() for word in ["data", "logical", "analyze", "interesting", "suggest", "list", "facts"])
        
        # Verify dialogue structure
        assert len(dialogue) == 2
        assert dialogue[0][0] == "Alice"
        assert dialogue[1][0] == "Bob"
    
    @pytest.mark.asyncio
    async def test_memory_accumulation(self, alice_perceptor, bob_perceptor):
        """Test that memories accumulate over conversation"""
        messages = [
            "Let's discuss the weather.",
            "It's quite sunny today.",
            "Perfect for a walk in the park."
        ]
        
        # Process messages through Alice's perceptor
        for msg in messages:
            stimulus = Stimulus(content=msg, type=StimulusType.user_message)
            perceptions = await alice_perceptor.perceive(stimulus)
            
            # Check that memories are building up
            memory_perceptions = [p for p in perceptions if p.source == "alice_memory"]
            assert len(memory_perceptions) <= len(messages)
        
        # Final perception should have access to all memories
        final_stimulus = Stimulus(
            content="What were we talking about?",
            type=StimulusType.user_message
        )
        final_perceptions = await alice_perceptor.perceive(final_stimulus)
        memory_perceptions = [p for p in final_perceptions if p.source == "alice_memory"]
        
        # Should have memories of previous messages
        assert len(memory_perceptions) >= 1
        # Check that we have some memories
        assert len(memory_perceptions) >= 1
        # Check memory content includes recent messages
        all_memory_content = " ".join(p.content for p in memory_perceptions)
        assert "discuss" in all_memory_content or "sunny" in all_memory_content or "park" in all_memory_content
    
    @pytest.mark.asyncio
    async def test_perception_confidence_levels(self, alice_perceptor):
        """Test that perceptions have appropriate confidence levels"""
        stimulus = Stimulus(
            content="Tell me about your favorite book.",
            type=StimulusType.user_message
        )
        
        perceptions = await alice_perceptor.perceive(stimulus)
        
        # Current input should have highest confidence
        current_perception = next(p for p in perceptions if p.source == "current_input")
        assert current_perception.confidence == 1.0
        
        # Memory perceptions should have lower confidence
        memory_perceptions = [p for p in perceptions if p.source == "alice_memory"]
        for mp in memory_perceptions:
            assert mp.confidence < 1.0
            assert mp.confidence > 0.0
    
    def test_scenario_evaluation_logic(self):
        """Test the evaluation logic without actual API calls"""
        # Mock critique scores
        mock_critiques = [
            {"average_score": 8.5, "personality_consistency": 9, "natural_flow": 8},
            {"average_score": 7.2, "personality_consistency": 7, "natural_flow": 7.5},
            {"average_score": 6.8, "personality_consistency": 7, "natural_flow": 6.5},
            {"average_score": 8.0, "personality_consistency": 8.5, "natural_flow": 7.5},
            {"average_score": 7.5, "personality_consistency": 8, "natural_flow": 7}
        ]
        
        # Test passing threshold
        PASSING_THRESHOLD = 7.0
        passed_count = sum(1 for c in mock_critiques if c["average_score"] >= PASSING_THRESHOLD)
        
        assert passed_count == 4  # 4 out of 5 should pass
        
        # Test overall average
        total_score = sum(c["average_score"] for c in mock_critiques)
        avg_score = total_score / len(mock_critiques)
        
        assert avg_score > 7.0  # Should be above threshold
        assert passed_count >= 3  # Majority should pass