"""Example of how an external package would use kairix-core testing utilities.

This example shows how a package that depends on kairix-core can leverage
the provided mock infrastructure for testing.
"""

# Imagine this is in a separate package that depends on kairix-core

# File: my_ai_app/agents/custom_agent.py
from kairix_core.cognition.persona import Persona
from kairix_core.cognition.perceptor import Perceptor
from kairix_core.types.cognition import Stimulus, Perception, StimulusType
from kairix_core.runtime.agent import AgentRuntime
from typing import List, AsyncIterator


class CustomPerceptor(Perceptor):
    """A custom perceptor for my application."""
    
    def __init__(self, data_source: str):
        self.data_source = data_source
    
    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        # Custom perception logic
        if stimulus.type == StimulusType.user_message:
            return [Perception(
                source=f"custom_{self.data_source}",
                content=f"Data from {self.data_source}: {stimulus.content}",
                confidence=0.95
            )]
        return []


class MyCustomPersona(Persona):
    """A custom persona that uses multiple perceptors."""
    
    def __init__(self, perceptors: List[Perceptor], agent_runtime: AgentRuntime):
        self.perceptors = perceptors
        self.agent_runtime = agent_runtime
    
    async def react(self, stimulus: Stimulus) -> AsyncIterator[str]:
        # Gather perceptions
        all_perceptions = []
        for perceptor in self.perceptors:
            perceptions = await perceptor.perceive(stimulus)
            all_perceptions.extend(perceptions)
        
        # Use agent runtime to generate response
        prompt = f"Respond based on: {[p.content for p in all_perceptions]}"
        result = self.agent_runtime.run("default", prompt)
        
        # Stream the response
        for char in result.data:
            yield char


# File: tests/conftest.py
# This is how the external package would set up testing
"""
from kairix_core.testing.conftest import *  # noqa: F403

# Add any project-specific fixtures here
"""


# File: tests/test_custom_agent.py
"""
import pytest
from my_ai_app.agents.custom_agent import CustomPerceptor, MyCustomPersona
from kairix_core.types.cognition import Stimulus, StimulusType
from kairix_core.testing.conftest import MockPerceptor


class TestCustomAgent:
    
    @pytest.mark.asyncio
    async def test_custom_perceptor(self):
        # Test our custom perceptor
        perceptor = CustomPerceptor("database")
        stimulus = Stimulus(content="test query", type=StimulusType.user_message)
        
        perceptions = await perceptor.perceive(stimulus)
        assert len(perceptions) == 1
        assert perceptions[0].source == "custom_database"
        assert "Data from database" in perceptions[0].content
    
    @pytest.mark.asyncio 
    async def test_custom_persona_with_mocks(
        self,
        mock_agent_runtime,
        mock_conversation_history_perceptor,
        mock_environmental_context_perceptor
    ):
        # Create persona with mix of real and mock perceptors
        custom_perceptor = CustomPerceptor("api")
        
        persona = MyCustomPersona(
            perceptors=[
                custom_perceptor,
                mock_conversation_history_perceptor,
                mock_environmental_context_perceptor
            ],
            agent_runtime=mock_agent_runtime
        )
        
        # Test the persona
        stimulus = Stimulus(content="Hello!", type=StimulusType.user_message)
        
        response = ""
        async for chunk in persona.react(stimulus):
            response += chunk
        
        # The response comes from mock_agent_runtime
        assert response == "Mock response"
        
        # Verify agent was called
        mock_agent_runtime.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_integration_with_complete_environment(self, complete_mock_environment):
        # Use complete mock environment for integration testing
        env = complete_mock_environment
        
        # All runtime components are available
        agent_runtime = env['agent_runtime']
        neo4j_runtime = env['neo4j_runtime']
        
        # Create and test custom components
        persona = MyCustomPersona(
            perceptors=[CustomPerceptor("test")],
            agent_runtime=agent_runtime
        )
        
        stimulus = Stimulus(content="test", type=StimulusType.user_message)
        response = ""
        async for chunk in persona.react(stimulus):
            response += chunk
        
        assert response == "Mock response"
    
    def test_custom_perceptor_with_mock_pattern(self):
        # You can also create custom mock patterns
        from kairix_core.testing.conftest import MockPerceptor
        from kairix_core.types.cognition import Perception
        
        # Create a mock that behaves like our custom perceptor
        mock_custom = MockPerceptor(
            name="custom_api",
            perceptions=[
                Perception(
                    source="custom_api",
                    content="Mocked API response",
                    confidence=0.99
                )
            ]
        )
        
        # Use it in tests...
        assert mock_custom.name == "custom_api"
"""

print("This example shows how external packages can use kairix-core testing utilities.")
print("The key steps are:")
print("1. Import fixtures in your conftest.py: from kairix_core.testing.conftest import *")
print("2. Use the provided mocks in your tests")
print("3. Mix real and mock components as needed")
print("4. Create custom mocks following the provided patterns")