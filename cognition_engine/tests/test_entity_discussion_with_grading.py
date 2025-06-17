"""
Test entity discussions with grading using the agents API.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime
import pytest
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.logging import RichHandler

from cognition_engine.configuration.runner import (
    CognitionAgentRunner,
    AgentConfigurationSet,
    AgentConfig
)
from agents import Agent as OpenAIAgent
from pydantic import BaseModel


# Setup logging
logging.basicConfig(level="INFO", datefmt="[%X]", handlers=[RichHandler()], force=True)
logger = logging.getLogger(__name__)
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


class EntityConversationSystem:
    """Manages conversations between two entities"""
    
    def __init__(self, runner: CognitionAgentRunner):
        self.runner = runner
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
        
        # Generate response
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
        """Grade a conversation using a grader agent"""
        
        # Format dialogue
        dialogue_text = "\n".join([f"{turn.speaker}: {turn.message}" for turn in dialogue])
        
        # Create grading prompt
        grading_prompt = f"""You are an expert conversation analyst. Evaluate this dialogue between Alice and Bob.

Scenario: {scenario.name}
Description: {scenario.description}
Expected Themes: {', '.join(scenario.expected_themes)}

Alice's Personality: {json.dumps(self.alice_personality, indent=2)}
Bob's Personality: {json.dumps(self.bob_personality, indent=2)}

DIALOGUE:
{dialogue_text}

Provide a structured evaluation with scores from 0-10 for:
1. personality_consistency - How well each speaker maintained their character
2. natural_flow - How natural and coherent the conversation feels
3. theme_coverage - How well the expected themes were addressed
4. overall_quality - Overall dialogue quality and engagement

Also list 2-3 strengths and weaknesses, and provide detailed feedback.

Respond with a JSON object with this exact structure:
{{
    "personality_consistency": <number>,
    "natural_flow": <number>,
    "theme_coverage": <number>,
    "overall_quality": <number>,
    "average_score": <average of the 4 scores>,
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "detailed_feedback": "Your detailed analysis"
}}"""
        
        # Create grader agent with JSON output
        grader = OpenAIAgent(
            name="grader",
            instructions=grading_prompt,
            output_type=DialogueCritique
        )
        
        # Get critique
        result = await self.runner.run(grader, "Please evaluate the dialogue above.")
        critique = result.final_output_as(DialogueCritique)
        
        return critique


# Test scenarios
def get_test_scenarios() -> List[ConversationScenario]:
    """Get all test scenarios"""
    return [
        ConversationScenario(
            name="Coffee Shop Reunion",
            description="Two old friends meet after years apart",
            initial_message="Oh wow, is that really you? It's been so long!",
            expected_themes=["nostalgia", "catching up", "life changes", "memories"],
            max_turns=6
        ),
        ConversationScenario(
            name="Project Planning",
            description="Planning a new collaborative project",
            initial_message="I've been thinking about that app idea we discussed. Want to explore it?",
            expected_themes=["collaboration", "ideas", "planning", "roles"],
            max_turns=8
        ),
        ConversationScenario(
            name="Philosophy Discussion",
            description="Discussing the meaning of success",
            initial_message="What does success mean to you in life?",
            expected_themes=["values", "perspectives", "meaning", "goals"],
            max_turns=6
        ),
        ConversationScenario(
            name="Problem Solving",
            description="Working through a technical challenge",
            initial_message="We need to fix this performance issue in the system.",
            expected_themes=["analysis", "solutions", "technical details", "collaboration"],
            max_turns=8
        ),
        ConversationScenario(
            name="Creative Brainstorm",
            description="Brainstorming ideas for an art installation",
            initial_message="I want to create something that connects technology and human emotion.",
            expected_themes=["creativity", "innovation", "art", "technology"],
            max_turns=6
        )
    ]


class TestEntityDiscussions:
    """Test entity discussion scenarios"""
    
    PASSING_THRESHOLD = 7.0
    
    @pytest.fixture
    def runner(self):
        """Create test runner"""
        config = AgentConfigurationSet(
            name="test_discussions",
            default_provider="openai",
            description="Test configuration",
            agent_configs={
                "alice_agent": AgentConfig(
                    name="alice_agent",
                    model="gpt-4o-mini",
                    temperature=0.8,
                    max_tokens=100
                ),
                "bob_agent": AgentConfig(
                    name="bob_agent", 
                    model="gpt-4o-mini",
                    temperature=0.7,
                    max_tokens=100
                ),
                "grader": AgentConfig(
                    name="grader",
                    model="gpt-4o-mini",
                    temperature=0.3,
                    max_tokens=500
                )
            }
        )
        
        from agents import OpenAIProvider
        provider = OpenAIProvider()
        
        return CognitionAgentRunner(config, {"openai": provider})
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", get_test_scenarios())
    async def test_scenario(self, runner, scenario):
        """Test a single scenario"""
        system = EntityConversationSystem(runner)
        
        # Run conversation
        dialogue = await system.run_conversation(scenario)
        
        # Grade it
        critique = await system.grade_conversation(scenario, dialogue)
        
        # Display results
        console.print(Panel(
            f"[bold]Results for {scenario.name}[/bold]\n\n"
            f"Personality Consistency: {critique.personality_consistency}/10\n"
            f"Natural Flow: {critique.natural_flow}/10\n"
            f"Theme Coverage: {critique.theme_coverage}/10\n"
            f"Overall Quality: {critique.overall_quality}/10\n"
            f"[bold green]Average: {critique.average_score}/10[/bold green]\n\n"
            f"Strengths: {', '.join(critique.strengths)}\n"
            f"Weaknesses: {', '.join(critique.weaknesses)}\n\n"
            f"Feedback: {critique.detailed_feedback}",
            title="Grading Results"
        ))
        
        # Check if passing
        passed = critique.average_score >= self.PASSING_THRESHOLD
        status = "✅ PASSED" if passed else "❌ FAILED"
        console.print(f"\n[bold]{status}[/bold] (Score: {critique.average_score:.1f}, Threshold: {self.PASSING_THRESHOLD})")
        
        # Assert passing
        assert critique.average_score >= self.PASSING_THRESHOLD, \
            f"Scenario '{scenario.name}' failed with score {critique.average_score:.1f}"
    
    @pytest.mark.asyncio 
    async def test_all_scenarios_summary(self, runner):
        """Run all scenarios and provide summary"""
        system = EntityConversationSystem(runner)
        scenarios = get_test_scenarios()
        results = []
        
        for scenario in scenarios:
            dialogue = await system.run_conversation(scenario)
            critique = await system.grade_conversation(scenario, dialogue)
            results.append({
                "scenario": scenario.name,
                "score": critique.average_score,
                "passed": critique.average_score >= self.PASSING_THRESHOLD
            })
        
        # Summary table
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
        
        # Need majority to pass
        assert passed_count >= 3, f"Only {passed_count}/5 scenarios passed. Need at least 3."
        assert avg_score >= 6.5, f"Overall average {avg_score:.1f} below 6.5 threshold"