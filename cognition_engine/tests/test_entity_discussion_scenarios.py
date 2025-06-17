"""
Test suite for entity discussion scenarios using the cognition engine.
Tests conversations between two distinct entities with different personalities.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import pytest
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.logging import RichHandler

from cognition_engine import (
    Stimulus, 
    StimulusType,
    Perception,
    Action,
    Perceptor,
    Proposer
)
from cognition_engine.configuration.runner import (
    CognitionAgentRunner,
    AgentConfigurationSet,
    AgentConfig
)
# Executor imported from main module
from agents import OpenAIProvider, Agent as OpenAIAgent
from openai import OpenAI

# Setup logging
logging.basicConfig(level="INFO", datefmt="[%X]", handlers=[RichHandler()], force=True)
logger = logging.getLogger(__name__)
console = Console()


@dataclass
class Memory:
    """Simple memory storage for entities"""
    content: str
    timestamp: datetime
    source: str
    embedding: Optional[List[float]] = None


@dataclass
class EntityMemoryStore:
    """In-memory storage for entity memories"""
    entity_name: str
    memories: List[Memory] = field(default_factory=list)
    
    def add_memory(self, content: str, source: str = "conversation"):
        """Add a new memory"""
        memory = Memory(
            content=content,
            timestamp=datetime.now(),
            source=source
        )
        self.memories.append(memory)
        logger.debug(f"{self.entity_name} stored memory: {content[:50]}...")
    
    def search_memories(self, query: str, k: int = 5) -> List[str]:
        """Simple keyword-based memory search"""
        # For testing, just return the k most recent memories that contain any query word
        query_words = query.lower().split()
        relevant_memories = []
        
        for memory in reversed(self.memories):  # Most recent first
            if any(word in memory.content.lower() for word in query_words):
                relevant_memories.append(memory.content)
                if len(relevant_memories) >= k:
                    break
        
        # If not enough relevant memories, add recent ones
        if len(relevant_memories) < k:
            for memory in reversed(self.memories):
                if memory.content not in relevant_memories:
                    relevant_memories.append(memory.content)
                    if len(relevant_memories) >= k:
                        break
        
        return relevant_memories[:k]


class ConversationPerceptor(Perceptor):
    """Perceptor that processes conversation and stores memories"""
    
    def __init__(self, entity_name: str, memory_store: EntityMemoryStore):
        self.entity_name = entity_name
        self.memory_store = memory_store
    
    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        """Process stimulus and create perceptions"""
        perceptions = []
        
        if stimulus.type == StimulusType.user_message:
            # Store the conversation in memory
            self.memory_store.add_memory(stimulus.content, source="conversation")
            
            # Search for relevant memories
            relevant_memories = self.memory_store.search_memories(stimulus.content, k=3)
            
            # Create perceptions from memories
            for memory in relevant_memories:
                perceptions.append(Perception(
                    content=f"I remember: {memory}",
                    source=f"{self.entity_name}_memory",
                    confidence=0.8
                ))
            
            # Add current conversation perception
            perceptions.append(Perception(
                content=stimulus.content,
                source="current_conversation",
                confidence=1.0
            ))
        
        return perceptions


class EntityResponseProposer(Proposer):
    """Proposer that generates responses based on entity personality"""
    
    def __init__(self, entity_name: str, personality_traits: Dict[str, Any]):
        self.entity_name = entity_name
        self.personality_traits = personality_traits
    
    async def consider(self, stimulus: Stimulus, perceptions: List[Perception]):
        """Generate response action based on personality"""
        if stimulus.type == StimulusType.user_message:
            # Compile context from perceptions
            memory_context = "\n".join([
                p.content for p in perceptions 
                if p.source.endswith("_memory")
            ])
            
            return Action(
                type="entity_response",
                parameters={
                    "entity_name": self.entity_name,
                    "personality": self.personality_traits,
                    "memories": memory_context,
                    "current_message": stimulus.content,
                    "perceptions": perceptions
                }
            )
        return None


@dataclass
class DialogueTurn:
    """Represents a single turn in the dialogue"""
    speaker: str
    message: str
    timestamp: datetime
    perceptions: List[Perception] = field(default_factory=list)


@dataclass
class Scenario:
    """Defines a test scenario"""
    name: str
    description: str
    initial_message: str
    expected_themes: List[str]
    max_turns: int = 10
    success_criteria: Dict[str, Any] = field(default_factory=dict)


class DialogueOrchestrator:
    """Orchestrates conversations between two entities"""
    
    def __init__(self, 
                 entity1_name: str,
                 entity1_personality: Dict[str, Any],
                 entity2_name: str, 
                 entity2_personality: Dict[str, Any],
                 runner: CognitionAgentRunner):
        
        # Create memory stores
        self.entity1_memory = EntityMemoryStore(entity1_name)
        self.entity2_memory = EntityMemoryStore(entity2_name)
        
        # Create perceptors
        self.entity1_perceptor = ConversationPerceptor(entity1_name, self.entity1_memory)
        self.entity2_perceptor = ConversationPerceptor(entity2_name, self.entity2_memory)
        
        # Create proposers
        self.entity1_proposer = EntityResponseProposer(entity1_name, entity1_personality)
        self.entity2_proposer = EntityResponseProposer(entity2_name, entity2_personality)
        
        # Store configuration
        self.entity1_name = entity1_name
        self.entity2_name = entity2_name
        self.entity1_personality = entity1_personality
        self.entity2_personality = entity2_personality
        self.runner = runner
        
        # Track dialogue
        self.dialogue_history: List[DialogueTurn] = []
    
    async def generate_response(self, entity_name: str, stimulus: Stimulus) -> str:
        """Generate a response from an entity"""
        # Select appropriate perceptor and proposer
        if entity_name == self.entity1_name:
            perceptor = self.entity1_perceptor
            proposer = self.entity1_proposer
            personality = self.entity1_personality
        else:
            perceptor = self.entity2_perceptor
            proposer = self.entity2_proposer
            personality = self.entity2_personality
        
        # Get perceptions
        perceptions = await perceptor.perceive(stimulus)
        
        # Get proposed action
        action = await proposer.consider(stimulus, perceptions)
        
        if action:
            # Create prompt for response generation
            memory_context = action.parameters.get("memories", "")
            personality_str = ", ".join([f"{k}: {v}" for k, v in personality.items()])
            
            prompt = f"""You are {entity_name} with the following personality traits: {personality_str}

Your memories:
{memory_context if memory_context else "No relevant memories yet."}

Current message: {stimulus.content}

Respond naturally as {entity_name} would, staying true to your personality. Keep responses concise (1-2 sentences)."""
            
            # Generate response using the runner
            agent = OpenAIAgent(
                name="dialogue_agent",
                instructions=prompt
            )
            
            result = await self.runner.run(agent, stimulus.content)
            response = result.final_output_as(str)
            
            # Record the turn
            turn = DialogueTurn(
                speaker=entity_name,
                message=response,
                timestamp=datetime.now(),
                perceptions=perceptions
            )
            self.dialogue_history.append(turn)
            
            return response
        
        return f"{entity_name}: I'm not sure how to respond."
    
    async def run_scenario(self, scenario: Scenario) -> Dict[str, Any]:
        """Run a complete scenario"""
        console.print(Panel(f"[bold cyan]Starting Scenario: {scenario.name}[/bold cyan]"))
        console.print(f"[italic]{scenario.description}[/italic]\n")
        
        # Clear dialogue history
        self.dialogue_history = []
        
        # Start with initial message to entity1
        current_message = scenario.initial_message
        current_speaker = self.entity2_name  # Start with entity2 so entity1 responds first
        
        for turn in range(scenario.max_turns):
            # Switch speaker
            if current_speaker == self.entity1_name:
                current_speaker = self.entity2_name
            else:
                current_speaker = self.entity1_name
            
            # Create stimulus
            stimulus = Stimulus(
                content=current_message,
                type=StimulusType.user_message
            )
            
            # Generate response
            response = await self.generate_response(current_speaker, stimulus)
            
            # Display the turn
            console.print(f"[bold green]{current_speaker}:[/bold green] {response}")
            
            # Update current message for next turn
            current_message = response
            
            # Check if conversation has reached a natural end
            if any(end_phrase in response.lower() for end_phrase in ["goodbye", "bye", "see you", "talk later"]):
                break
        
        return {
            "scenario": scenario,
            "dialogue": self.dialogue_history,
            "turns": len(self.dialogue_history)
        }
    
    def display_dialogue(self):
        """Display the dialogue history in a nice format"""
        table = Table(title="Dialogue History")
        table.add_column("Turn", style="cyan", width=6)
        table.add_column("Speaker", style="green", width=15)
        table.add_column("Message", style="white", width=60)
        
        for i, turn in enumerate(self.dialogue_history):
            table.add_row(
                str(i + 1),
                turn.speaker,
                turn.message
            )
        
        console.print(table)


class ScenarioCritique:
    """Uses O3 reasoning agent to critique dialogues"""
    
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
    
    async def critique_dialogue(self, 
                               scenario: Scenario, 
                               dialogue: List[DialogueTurn],
                               entity1_personality: Dict[str, Any],
                               entity2_personality: Dict[str, Any]) -> Dict[str, Any]:
        """Critique a dialogue using O3 reasoning"""
        
        # Format dialogue for critique
        dialogue_text = "\n".join([
            f"{turn.speaker}: {turn.message}" 
            for turn in dialogue
        ])
        
        # Create critique prompt
        critique_prompt = f"""As an expert dialogue analyst, critique the following conversation between two entities.

Scenario: {scenario.name}
Description: {scenario.description}
Initial Message: {scenario.initial_message}

Entity 1 Personality: {json.dumps(entity1_personality, indent=2)}
Entity 2 Personality: {json.dumps(entity2_personality, indent=2)}

Expected Themes: {', '.join(scenario.expected_themes)}

DIALOGUE:
{dialogue_text}

Please evaluate:
1. How well each entity maintained their personality traits (0-10)
2. Natural flow and coherence of the conversation (0-10)
3. Coverage of expected themes (0-10)
4. Overall realism and engagement (0-10)
5. Specific strengths and weaknesses

Provide your response as JSON with the following structure:
{{
    "personality_consistency": <score>,
    "natural_flow": <score>,
    "theme_coverage": <score>,
    "overall_quality": <score>,
    "average_score": <average of all scores>,
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "detailed_feedback": "Your detailed analysis"
}}"""
        
        # Use O3-mini for reasoning
        response = self.client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": "You are an expert dialogue analyst providing structured critiques."},
                {"role": "user", "content": critique_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        critique = json.loads(response.choices[0].message.content)
        return critique


class EntityDiscussionTestSuite:
    """Main test suite for entity discussions"""
    
    # Define passing threshold
    PASSING_SCORE_THRESHOLD = 7.0
    
    @classmethod
    def create_test_scenarios(cls) -> List[Scenario]:
        """Define the 5 test scenarios"""
        return [
            Scenario(
                name="Coffee Shop Meeting",
                description="Two old friends meet at a coffee shop after years apart",
                initial_message="Oh my goodness, is that really you? It's been ages!",
                expected_themes=["nostalgia", "catching up", "shared memories", "life changes"],
                max_turns=8,
                success_criteria={"min_nostalgia_mentions": 2}
            ),
            
            Scenario(
                name="Business Negotiation",
                description="A cautious investor meets with an enthusiastic entrepreneur",
                initial_message="Thank you for meeting with me. I believe my startup could revolutionize the industry.",
                expected_themes=["business model", "risks", "investment", "growth potential"],
                max_turns=10,
                success_criteria={"covers_risks": True, "mentions_roi": True}
            ),
            
            Scenario(
                name="Philosophy Debate",
                description="A pragmatist and an idealist discuss the meaning of success",
                initial_message="What does success mean to you in today's world?",
                expected_themes=["values", "practical vs ideal", "happiness", "achievement"],
                max_turns=8,
                success_criteria={"philosophical_depth": True}
            ),
            
            Scenario(
                name="Emergency Planning",
                description="Two roommates discuss preparing for a coming storm",
                initial_message="Have you seen the weather forecast? We need to prepare for the storm.",
                expected_themes=["supplies", "safety", "coordination", "urgency"],
                max_turns=6,
                success_criteria={"action_items": True}
            ),
            
            Scenario(
                name="Creative Collaboration",
                description="An artist and a technologist brainstorm an interactive installation",
                initial_message="I have this vision for an installation that responds to people's emotions.",
                expected_themes=["creativity", "technology", "user experience", "artistic vision"],
                max_turns=10,
                success_criteria={"innovative_ideas": True}
            )
        ]
    
    @pytest.fixture
    def test_runner(self):
        """Create test runner with OpenAI configuration"""
        config_set = AgentConfigurationSet(
            name="dialogue_test",
            default_provider="openai",
            description="Configuration for dialogue testing",
            agent_configs={
                "dialogue_agent": AgentConfig(
                    name="dialogue_agent",
                    model="gpt-4o-mini",
                    temperature=0.8,
                    max_tokens=150
                )
            }
        )
        
        # Use actual OpenAI provider from environment
        provider = OpenAIProvider()
        
        return CognitionAgentRunner(config_set, {"openai": provider})
    
    @pytest.fixture
    def entity_personalities(self):
        """Define the two entity personalities"""
        alice_personality = {
            "trait_openness": "high",
            "trait_conscientiousness": "medium", 
            "communication_style": "warm and empathetic",
            "decision_making": "intuitive",
            "interests": ["art", "human connections", "philosophy"],
            "quirks": ["uses metaphors frequently", "asks thoughtful questions"]
        }
        
        bob_personality = {
            "trait_openness": "medium",
            "trait_conscientiousness": "high",
            "communication_style": "logical and structured", 
            "decision_making": "analytical",
            "interests": ["technology", "efficiency", "problem-solving"],
            "quirks": ["likes data and facts", "makes lists"]
        }
        
        return alice_personality, bob_personality
    
    @pytest.mark.asyncio
    async def test_all_scenarios(self, test_runner, entity_personalities):
        """Run all 5 scenarios and evaluate results"""
        alice_personality, bob_personality = entity_personalities
        
        # Create orchestrator
        orchestrator = DialogueOrchestrator(
            entity1_name="Alice",
            entity1_personality=alice_personality,
            entity2_name="Bob",
            entity2_personality=bob_personality,
            runner=test_runner
        )
        
        # Create critique system
        critique_system = ScenarioCritique(OpenAI())
        
        # Get all scenarios
        scenarios = self.create_test_scenarios()
        
        # Track results
        all_results = []
        
        for scenario in scenarios:
            console.print(f"\n[bold yellow]{'='*60}[/bold yellow]")
            
            # Run scenario
            result = await orchestrator.run_scenario(scenario)
            
            # Display dialogue
            orchestrator.display_dialogue()
            
            # Get critique
            critique = await critique_system.critique_dialogue(
                scenario,
                result["dialogue"],
                alice_personality,
                bob_personality
            )
            
            # Display critique
            console.print(Panel(
                f"[bold]Critique for: {scenario.name}[/bold]\n\n"
                f"Personality Consistency: {critique['personality_consistency']}/10\n"
                f"Natural Flow: {critique['natural_flow']}/10\n"
                f"Theme Coverage: {critique['theme_coverage']}/10\n"
                f"Overall Quality: {critique['overall_quality']}/10\n"
                f"[bold green]Average Score: {critique['average_score']}/10[/bold green]\n\n"
                f"Strengths: {', '.join(critique['strengths'])}\n"
                f"Weaknesses: {', '.join(critique['weaknesses'])}\n\n"
                f"Detailed Feedback:\n{critique['detailed_feedback']}",
                title="O3 Reasoning Critique"
            ))
            
            # Check if passing
            passed = critique['average_score'] >= self.PASSING_SCORE_THRESHOLD
            console.print(
                f"\n[bold]Result: {'✅ PASSED' if passed else '❌ FAILED'}[/bold] "
                f"(Score: {critique['average_score']:.1f}, Threshold: {self.PASSING_SCORE_THRESHOLD})"
            )
            
            all_results.append({
                "scenario": scenario.name,
                "score": critique['average_score'],
                "passed": passed,
                "critique": critique
            })
        
        # Summary
        console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
        console.print("[bold]SUMMARY OF ALL SCENARIOS[/bold]\n")
        
        summary_table = Table(title="Scenario Results")
        summary_table.add_column("Scenario", style="cyan")
        summary_table.add_column("Score", style="yellow")
        summary_table.add_column("Result", style="green")
        
        total_score = 0
        passed_count = 0
        
        for result in all_results:
            summary_table.add_row(
                result["scenario"],
                f"{result['score']:.1f}/10",
                "✅ PASSED" if result["passed"] else "❌ FAILED"
            )
            total_score += result["score"]
            if result["passed"]:
                passed_count += 1
        
        console.print(summary_table)
        
        avg_score = total_score / len(all_results)
        console.print(f"\n[bold]Overall Average Score: {avg_score:.1f}/10[/bold]")
        console.print(f"[bold]Scenarios Passed: {passed_count}/{len(all_results)}[/bold]")
        
        # Assert that majority pass
        assert passed_count >= 3, f"Only {passed_count}/5 scenarios passed. Need at least 3 to pass."
        assert avg_score >= 6.5, f"Overall average score {avg_score:.1f} is below 6.5 threshold"


if __name__ == "__main__":
    # Run the test suite directly
    pytest.main([__file__, "-v", "-s"])