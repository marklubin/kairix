"""
Standalone test for entity discussions with mocking.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cognition_engine.configuration.runner import CognitionAgentRunner
from agents import Agent as OpenAIAgent, RunResult
from pydantic import BaseModel


console = Console()


class DialogueCritique(BaseModel):
    """Structured critique output"""
    personality_consistency: float
    natural_flow: float
    theme_coverage: float
    overall_quality: float
    average_score: float
    strengths: List[str]
    weaknesses: List[str]
    detailed_feedback: str


@dataclass
class Memory:
    """Simple memory storage"""
    content: str
    timestamp: datetime
    source: str


@dataclass
class MemoryStore:
    """In-memory storage for entity memories"""
    entity_name: str
    memories: List[Memory] = field(default_factory=list)
    
    def add_memory(self, content: str):
        self.memories.append(Memory(
            content=content,
            timestamp=datetime.now(),
            source="conversation"
        ))
    
    def get_recent_memories(self, k: int = 3) -> List[str]:
        """Get k most recent memories"""
        return [m.content for m in self.memories[-k:]]


@dataclass
class DialogueTurn:
    """A single turn in dialogue"""
    speaker: str
    message: str
    timestamp: datetime


@dataclass
class ConversationScenario:
    """Test scenario definition"""
    name: str
    description: str
    initial_message: str
    expected_themes: List[str]
    max_turns: int = 8


class MockedEntitySystem:
    """Entity conversation system with mocked responses"""
    
    def __init__(self, mock_runner):
        self.runner = mock_runner
        self.alice_memory = MemoryStore("Alice")
        self.bob_memory = MemoryStore("Bob")
        self.dialogue_history: List[DialogueTurn] = []
        
        # Define personalities
        self.alice_personality = {
            "traits": "warm, empathetic, creative, philosophical",
            "style": "uses metaphors, asks thoughtful questions",
            "interests": "art, human connections, deep conversations"
        }
        
        self.bob_personality = {
            "traits": "logical, analytical, practical, organized",
            "style": "data-driven, makes lists, structured thinking",
            "interests": "technology, efficiency, problem-solving"
        }
    
    async def generate_entity_response(self, 
                                     entity_name: str,
                                     message: str,
                                     personality: Dict[str, Any],
                                     memory_store: MemoryStore) -> str:
        """Generate a response from an entity"""
        
        # Get recent memories
        memories = memory_store.get_recent_memories(3)
        memory_context = "\n".join([f"- {m}" for m in memories]) if memories else "No previous memories"
        
        # Create prompt
        prompt = f"""You are {entity_name} with these characteristics:
{json.dumps(personality, indent=2)}

Recent conversation memories:
{memory_context}

Current message: {message}

Respond naturally as {entity_name}, staying true to your personality. Keep response concise (1-2 sentences)."""
        
        # Create agent
        agent = OpenAIAgent(
            name=f"{entity_name.lower()}_agent",
            instructions=prompt
        )
        
        # Generate response using mock
        result = await self.runner.run(agent, message)
        response = result.final_output_as(str)
        
        # Store in memory
        memory_store.add_memory(f"They said: {message}")
        memory_store.add_memory(f"I responded: {response}")
        
        return response
    
    async def run_conversation(self, scenario: ConversationScenario) -> List[DialogueTurn]:
        """Run a complete conversation scenario"""
        console.print(Panel(f"[bold cyan]Scenario: {scenario.name}[/bold cyan]\n{scenario.description}"))
        
        # Clear history
        self.dialogue_history = []
        current_message = scenario.initial_message
        
        # Alice starts
        speakers = ["Alice", "Bob"]
        memories = [self.alice_memory, self.bob_memory]
        personalities = [self.alice_personality, self.bob_personality]
        
        for turn in range(scenario.max_turns):
            speaker_idx = turn % 2
            speaker = speakers[speaker_idx]
            memory = memories[speaker_idx]
            personality = personalities[speaker_idx]
            
            # Generate response
            response = await self.generate_entity_response(
                speaker, current_message, personality, memory
            )
            
            # Record turn
            dialogue_turn = DialogueTurn(
                speaker=speaker,
                message=response,
                timestamp=datetime.now()
            )
            self.dialogue_history.append(dialogue_turn)
            
            # Display
            console.print(f"[bold green]{speaker}:[/bold green] {response}")
            
            # Update message for next turn
            current_message = response
            
            # Check for natural ending
            if any(phrase in response.lower() for phrase in ["goodbye", "bye", "talk later"]):
                break
        
        return self.dialogue_history
    
    async def grade_conversation(self, scenario: ConversationScenario, dialogue: List[DialogueTurn]) -> DialogueCritique:
        """Grade a conversation using mock grader"""
        
        # The mock will return a pre-defined critique
        grader = OpenAIAgent(
            name="grader",
            instructions="Grade the conversation",
            output_type=DialogueCritique
        )
        
        result = await self.runner.run(grader, "Please evaluate")
        critique = result.final_output_as(DialogueCritique)
        
        return critique


class TestEntityDiscussionsStandalone:
    """Test entity discussions with full mocking"""
    
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
        
        # Pre-defined critique
        grader_critique = DialogueCritique(
            personality_consistency=8.5,
            natural_flow=8.0,
            theme_coverage=7.5,
            overall_quality=8.0,
            average_score=8.0,
            strengths=["Clear personality distinction", "Natural conversation flow", "Good back-and-forth"],
            weaknesses=["Could explore themes more deeply", "Some responses feel generic"],
            detailed_feedback="The dialogue shows good personality consistency with Alice being creative and Bob being analytical. The conversation flows naturally."
        )
        
        response_count = {"alice": 0, "bob": 0}
        
        async def mock_run(agent, stimulus):
            result = Mock(spec=RunResult)
            
            # Determine response based on agent name
            if "alice" in agent.name:
                idx = response_count["alice"] % len(alice_responses)
                response = alice_responses[idx]
                response_count["alice"] += 1
            elif "bob" in agent.name:
                idx = response_count["bob"] % len(bob_responses)
                response = bob_responses[idx]
                response_count["bob"] += 1
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
    
    def get_test_scenarios(self) -> List[ConversationScenario]:
        """Get test scenarios"""
        return [
            ConversationScenario(
                name="Coffee Shop Reunion",
                description="Two old friends meet after years apart",
                initial_message="Oh wow, is that really you? It's been so long!",
                expected_themes=["nostalgia", "catching up", "life changes", "memories"],
                max_turns=4
            ),
            ConversationScenario(
                name="Project Planning",
                description="Planning a new collaborative project",
                initial_message="I've been thinking about that app idea we discussed. Want to explore it?",
                expected_themes=["collaboration", "ideas", "planning", "roles"],
                max_turns=4
            ),
            ConversationScenario(
                name="Philosophy Discussion",
                description="Discussing the meaning of success",
                initial_message="What does success mean to you in life?",
                expected_themes=["values", "perspectives", "meaning", "goals"],
                max_turns=4
            )
        ]
    
    @pytest.mark.asyncio
    async def test_single_scenario(self, mock_runner):
        """Test a single scenario with mocked responses"""
        system = MockedEntitySystem(mock_runner)
        
        scenario = ConversationScenario(
            name="Test Scenario",
            description="Testing conversation flow",
            initial_message="Hello! How are you today?",
            expected_themes=["greeting", "conversation"],
            max_turns=4
        )
        
        # Run conversation
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
        assert any(any(word in turn.message.lower() for word in ["wonderful", "beautiful", "resonates", "love", "creative", "exploring"])
                  for turn in alice_turns)
        
        # Bob should be more analytical
        assert any(any(word in turn.message.lower() for word in ["productive", "analyze", "practical", "optimize", "list", "data", "components"])
                  for turn in bob_turns)
        
        # Grade the conversation
        critique = await system.grade_conversation(scenario, dialogue)
        
        # Verify critique
        assert isinstance(critique, DialogueCritique)
        assert critique.average_score >= 7.0  # Should pass threshold
        assert len(critique.strengths) > 0
        assert len(critique.weaknesses) > 0
        
        # Display results
        console.print(Panel(
            f"[bold]Test Results[/bold]\n\n"
            f"Average Score: {critique.average_score}/10\n"
            f"Personality: {critique.personality_consistency}/10\n"
            f"Flow: {critique.natural_flow}/10\n"
            f"Themes: {critique.theme_coverage}/10\n"
            f"Quality: {critique.overall_quality}/10\n\n"
            f"Feedback: {critique.detailed_feedback}",
            title="Grading Results"
        ))
    
    @pytest.mark.asyncio
    async def test_all_scenarios(self, mock_runner):
        """Test all scenarios and verify they pass"""
        system = MockedEntitySystem(mock_runner)
        scenarios = self.get_test_scenarios()
        results = []
        
        for scenario in scenarios:
            console.print(f"\n[bold yellow]Running: {scenario.name}[/bold yellow]")
            
            # Run conversation
            dialogue = await system.run_conversation(scenario)
            
            # Grade it
            critique = await system.grade_conversation(scenario, dialogue)
            
            # Track results
            passed = critique.average_score >= 7.0
            results.append({
                "scenario": scenario.name,
                "score": critique.average_score,
                "passed": passed
            })
            
            status = "✅ PASSED" if passed else "❌ FAILED"
            console.print(f"Result: {status} (Score: {critique.average_score}/10)")
        
        # Summary
        table = Table(title="All Scenarios Summary")
        table.add_column("Scenario", style="cyan")
        table.add_column("Score", style="yellow") 
        table.add_column("Status", style="green")
        
        total_score = 0
        passed_count = 0
        
        for result in results:
            table.add_row(
                result["scenario"],
                f"{result['score']:.1f}/10",
                "✅ PASSED" if result["passed"] else "❌ FAILED"
            )
            total_score += result["score"]
            if result["passed"]:
                passed_count += 1
        
        console.print(table)
        
        avg_score = total_score / len(results)
        console.print(f"\n[bold]Overall Average: {avg_score:.1f}/10[/bold]")
        console.print(f"[bold]Passed: {passed_count}/{len(results)}[/bold]")
        
        # All should pass with mocked scores
        assert passed_count == len(results), f"Only {passed_count}/{len(results)} scenarios passed"
        assert avg_score >= 7.0, f"Average score {avg_score:.1f} below threshold"
    
    @pytest.mark.asyncio
    async def test_memory_accumulation(self, mock_runner):
        """Test that memories accumulate correctly"""
        system = MockedEntitySystem(mock_runner)
        
        # Run a short conversation
        scenario = ConversationScenario(
            name="Memory Test",
            description="Testing memory",
            initial_message="Hello!",
            expected_themes=["greeting"],
            max_turns=2
        )
        
        # Initially no memories
        assert len(system.alice_memory.memories) == 0
        assert len(system.bob_memory.memories) == 0
        
        await system.run_conversation(scenario)
        
        # Should have memories now
        assert len(system.alice_memory.memories) >= 2  # At least one exchange
        assert len(system.bob_memory.memories) >= 2
        
        # Verify memory content structure
        alice_memories = system.alice_memory.get_recent_memories(10)
        assert any("They said:" in m for m in alice_memories)
        assert any("I responded:" in m for m in alice_memories)