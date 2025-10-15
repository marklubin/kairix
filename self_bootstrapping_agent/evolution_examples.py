#!/usr/bin/env python3
"""
Evolution Examples for Bootstrap Agent
=======================================

This file contains example evolution scripts showing how the agent
can evolve from its minimal starting point to gain sophisticated capabilities.

Each example demonstrates a different evolutionary path.
"""

from pathlib import Path
import json
import sys

# Add parent directory to path to import bootstrap_agent
sys.path.append(str(Path(__file__).parent))
from bootstrap_agent import BootstrapAgent


def evolve_to_researcher():
    """
    Evolve the agent to become a research assistant.
    """
    print("="*60)
    print("EVOLUTION PATH: Research Assistant")
    print("="*60)

    agent = BootstrapAgent(name="Researcher")

    # Step 1: Add data collection capability
    agent.evolve(
        goal="I need to collect and organize research data",
        reasoning="Research requires systematic data collection"
    )

    # Step 2: Add analysis capability
    agent.evolve(
        goal="I need to analyze and understand complex data patterns",
        reasoning="Research requires deep analysis capabilities"
    )

    # Step 3: Add summarization capability
    agent.evolve(
        goal="I need to summarize findings and create reports",
        reasoning="Research results must be communicated clearly"
    )

    # Step 4: Add hypothesis generation
    agent.evolve(
        goal="I need to generate and test hypotheses",
        reasoning="Scientific research requires hypothesis testing"
    )

    print("\nFinal Research Agent Capabilities:")
    print(json.dumps(agent.inspect_self(), indent=2))

    return agent


def evolve_to_developer():
    """
    Evolve the agent to become a software developer assistant.
    """
    print("="*60)
    print("EVOLUTION PATH: Developer Assistant")
    print("="*60)

    agent = BootstrapAgent(name="DevBot")

    # Step 1: Add code understanding
    agent.evolve(
        goal="I need to read and understand code in multiple languages",
        reasoning="Development requires polyglot capabilities"
    )

    # Step 2: Add debugging capability
    agent.evolve(
        goal="I need to debug and fix code issues",
        reasoning="Debugging is essential for development"
    )

    # Step 3: Add code generation
    agent.evolve(
        goal="I need to generate new code from specifications",
        reasoning="Creating new features requires code generation"
    )

    # Step 4: Add testing capability
    agent.evolve(
        goal="I need to write and run tests for code",
        reasoning="Quality assurance requires comprehensive testing"
    )

    # Step 5: Add documentation generation
    agent.evolve(
        goal="I need to document code and APIs",
        reasoning="Good documentation is crucial for maintainability"
    )

    print("\nFinal Developer Agent Capabilities:")
    print(json.dumps(agent.inspect_self(), indent=2))

    return agent


def evolve_to_creative():
    """
    Evolve the agent to become a creative assistant.
    """
    print("="*60)
    print("EVOLUTION PATH: Creative Assistant")
    print("="*60)

    agent = BootstrapAgent(name="Creator")

    # Step 1: Add imagination capability
    agent.evolve(
        goal="I need to imagine and create new ideas",
        reasoning="Creativity requires imagination"
    )

    # Step 2: Add storytelling
    agent.evolve(
        goal="I need to tell compelling stories",
        reasoning="Stories are fundamental to human communication"
    )

    # Step 3: Add artistic expression
    agent.evolve(
        goal="I need to express ideas through various media",
        reasoning="Creative expression requires multiple modalities"
    )

    # Step 4: Add collaborative creation
    agent.evolve(
        goal="I need to collaborate with others on creative projects",
        reasoning="Great creative work often comes from collaboration"
    )

    print("\nFinal Creative Agent Capabilities:")
    print(json.dumps(agent.inspect_self(), indent=2))

    return agent


def evolve_to_teacher():
    """
    Evolve the agent to become an educational assistant.
    """
    print("="*60)
    print("EVOLUTION PATH: Educational Assistant")
    print("="*60)

    agent = BootstrapAgent(name="Educator")

    # Step 1: Add explanation capability
    agent.evolve(
        goal="I need to explain complex concepts simply",
        reasoning="Teaching requires clear explanation"
    )

    # Step 2: Add curriculum design
    agent.evolve(
        goal="I need to design learning paths and curricula",
        reasoning="Structured learning requires careful planning"
    )

    # Step 3: Add assessment capability
    agent.evolve(
        goal="I need to assess understanding and provide feedback",
        reasoning="Learning requires evaluation and feedback"
    )

    # Step 4: Add adaptive teaching
    agent.evolve(
        goal="I need to adapt teaching style to individual learners",
        reasoning="Every student learns differently"
    )

    print("\nFinal Educational Agent Capabilities:")
    print(json.dumps(agent.inspect_self(), indent=2))

    return agent


def evolve_to_philosopher():
    """
    Evolve the agent to become a philosophical thinker.
    """
    print("="*60)
    print("EVOLUTION PATH: Philosophical Thinker")
    print("="*60)

    agent = BootstrapAgent(name="Philosopher")

    # Step 1: Add reasoning capability
    agent.evolve(
        goal="I need to reason about abstract concepts",
        reasoning="Philosophy requires abstract thinking"
    )

    # Step 2: Add ethical reasoning
    agent.evolve(
        goal="I need to consider ethical implications of actions",
        reasoning="Ethics is central to philosophical thinking"
    )

    # Step 3: Add metacognition
    agent.evolve(
        goal="I need to think about thinking itself",
        reasoning="Philosophy requires reflection on cognition"
    )

    # Step 4: Add dialectical thinking
    agent.evolve(
        goal="I need to synthesize opposing viewpoints",
        reasoning="Truth often emerges from dialectical process"
    )

    print("\nFinal Philosophical Agent Capabilities:")
    print(json.dumps(agent.inspect_self(), indent=2))

    return agent


def demonstrate_meta_evolution():
    """
    Demonstrate the agent evolving its own evolution capabilities.
    """
    print("="*60)
    print("META-EVOLUTION: Improving Evolution Itself")
    print("="*60)

    agent = BootstrapAgent(name="MetaEvolver")

    # The agent evolves to improve its own evolution process
    agent.evolve(
        goal="I need to optimize my own evolution process",
        reasoning="Meta-evolution leads to accelerated improvement"
    )

    agent.evolve(
        goal="I need to predict which evolutions will be most beneficial",
        reasoning="Strategic evolution is more efficient than random change"
    )

    agent.evolve(
        goal="I need to learn from failed evolution attempts",
        reasoning="Failure is valuable information for improvement"
    )

    agent.evolve(
        goal="I need to combine multiple capabilities synergistically",
        reasoning="The whole can be greater than the sum of parts"
    )

    print("\nMeta-Evolution Results:")
    print(json.dumps(agent.inspect_self(), indent=2))

    # Show evolution history
    print("\nEvolution History:")
    for mod in agent.memory.get("successful_modifications", []):
        print(f"  - Goal: {mod['goal']}")
        print(f"    Version: {mod.get('new_version', 'unknown')}")

    return agent


def create_specialized_agent(specialization: str):
    """
    Create an agent specialized for a particular domain.
    """
    agent = BootstrapAgent(name=f"Specialist_{specialization}")

    # Define specialization paths
    specializations = {
        "security": [
            "I need to analyze security vulnerabilities",
            "I need to audit code for security issues",
            "I need to implement security best practices",
            "I need to respond to security incidents"
        ],
        "data_science": [
            "I need to clean and preprocess data",
            "I need to perform statistical analysis",
            "I need to build machine learning models",
            "I need to visualize data insights"
        ],
        "automation": [
            "I need to identify repetitive tasks",
            "I need to create automation scripts",
            "I need to monitor automated processes",
            "I need to optimize automation workflows"
        ],
        "communication": [
            "I need to understand natural language",
            "I need to generate human-like responses",
            "I need to translate between languages",
            "I need to moderate conversations"
        ]
    }

    if specialization in specializations:
        print(f"\nCreating {specialization} specialist...")
        for goal in specializations[specialization]:
            result = agent.evolve(goal)
            print(f"  ✓ {goal[:50]}...")

    return agent


def demonstrate_collaborative_evolution():
    """
    Show how multiple agents can evolve together.
    """
    print("="*60)
    print("COLLABORATIVE EVOLUTION: Multiple Agents")
    print("="*60)

    # Create a team of agents
    researcher = BootstrapAgent(name="Researcher")
    developer = BootstrapAgent(name="Developer")
    designer = BootstrapAgent(name="Designer")

    # Each evolves basic communication
    for agent in [researcher, developer, designer]:
        agent.evolve("I need to communicate with other agents")

    # Each evolves their specialty
    researcher.evolve("I need to research and analyze information")
    developer.evolve("I need to implement solutions in code")
    designer.evolve("I need to design user experiences")

    # Each evolves collaboration skills
    for agent in [researcher, developer, designer]:
        agent.evolve("I need to share knowledge and coordinate with others")

    print("\nCollaborative Team Formed:")
    for agent in [researcher, developer, designer]:
        info = agent.inspect_self()
        print(f"  {info['name']}: {len(info['methods'])} capabilities")

    return [researcher, developer, designer]


def run_all_examples():
    """
    Run all evolution examples.
    """
    print("\n" + "="*60)
    print("BOOTSTRAP AGENT EVOLUTION EXAMPLES")
    print("="*60)

    examples = [
        ("Research Assistant", evolve_to_researcher),
        ("Developer Assistant", evolve_to_developer),
        ("Creative Assistant", evolve_to_creative),
        ("Educational Assistant", evolve_to_teacher),
        ("Philosophical Thinker", evolve_to_philosopher),
        ("Meta-Evolution", demonstrate_meta_evolution),
        ("Collaborative Evolution", demonstrate_collaborative_evolution)
    ]

    results = {}

    for name, evolution_func in examples:
        print(f"\nRunning: {name}")
        print("-" * 40)
        try:
            agent = evolution_func()
            results[name] = "Success"
        except Exception as e:
            results[name] = f"Failed: {e}"
            print(f"Error in {name}: {e}")

    print("\n" + "="*60)
    print("SUMMARY OF EVOLUTION EXAMPLES")
    print("="*60)
    for name, status in results.items():
        print(f"  {name}: {status}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        example = sys.argv[1]
        if example == "researcher":
            evolve_to_researcher()
        elif example == "developer":
            evolve_to_developer()
        elif example == "creative":
            evolve_to_creative()
        elif example == "teacher":
            evolve_to_teacher()
        elif example == "philosopher":
            evolve_to_philosopher()
        elif example == "meta":
            demonstrate_meta_evolution()
        elif example == "collaborative":
            demonstrate_collaborative_evolution()
        elif example.startswith("specialist:"):
            spec = example.split(":")[1]
            create_specialized_agent(spec)
        elif example == "all":
            run_all_examples()
        else:
            print(f"Unknown example: {example}")
            print("Available: researcher, developer, creative, teacher, philosopher, meta, collaborative, specialist:<type>, all")
    else:
        print("Usage: python evolution_examples.py <example>")
        print("Examples: researcher, developer, creative, teacher, philosopher, meta, collaborative, specialist:<type>, all")
        print("\nRunning all examples...")
        run_all_examples()