# Kairix Test Dataset Generation Strategy

## Overview

This document outlines our strategy for generating and sourcing test datasets for the Kairix Engine testing infrastructure, combining existing benchmarks with custom scenario generation.

## 1. Existing Benchmark Datasets

### 1.1 General Intelligence & Reasoning

**MMLU (Massive Multitask Language Understanding)**
- Source: Hugging Face `cais/mmlu`
- Coverage: 57 subjects across STEM, humanities, social sciences
- Use case: General knowledge and reasoning baseline

```python
from datasets import load_dataset

mmlu_dataset = load_dataset("cais/mmlu", "all")
# Convert to our TestScenario format
scenarios = convert_mmlu_to_scenarios(mmlu_dataset)
```

**BigBench Hard (BBH)**
- Source: Hugging Face `lukaemon/bbh`
- Coverage: 23 challenging reasoning tasks
- Use case: Complex reasoning and multi-step problem solving

**GSM8K**
- Source: Hugging Face `gsm8k`
- Coverage: Grade school math word problems
- Use case: Mathematical reasoning

### 1.2 Conversational & Dialog Datasets

**PersonaChat**
- Source: Hugging Face `bavard/personachat_truecased`
- Coverage: Multi-turn conversations with personas
- Use case: Testing memory consistency across conversations

**Wizard of Wikipedia**
- Source: Hugging Face `wizard_of_wikipedia`
- Coverage: Knowledge-grounded conversations
- Use case: Testing factual memory integration

**EmpatheticDialogues**
- Source: Hugging Face `empathetic_dialogues`
- Coverage: Emotionally aware conversations
- Use case: Testing style and aesthetic responses

### 1.3 Tool Usage Datasets

**ToolBench**
- Source: Hugging Face `toolbench/toolbench`
- Coverage: 16,000+ real-world APIs
- Use case: Tool selection and parameter testing

**WebShop**
- Source: Hugging Face `webshop`
- Coverage: E-commerce navigation tasks
- Use case: Multi-step tool usage scenarios

### 1.4 Voice/Audio Datasets

**LibriSpeech**
- Source: Hugging Face `librispeech_asr`
- Coverage: 1000 hours of English speech
- Use case: Voice input testing

**VCTK**
- Source: Hugging Face `vctk`
- Coverage: 110 English speakers with various accents
- Use case: Voice diversity testing

## 2. Custom Dataset Generation Pipeline

### 2.1 Scenario Generator Framework

```python
class ScenarioGenerator:
    """Generate custom test scenarios based on templates and variations"""
    
    def __init__(self, llm_model: str = "gpt-4"):
        self.generator = OpenAI(model=llm_model)
        self.templates = self._load_templates()
        self.memory_corpus = self._load_memory_corpus()
    
    async def generate_memory_scenarios(
        self, 
        agent_profile: dict,
        num_scenarios: int = 50
    ) -> list[TestScenario]:
        """Generate scenarios that test memory recall"""
        
        scenarios = []
        
        # Generate conversation history
        history = await self._generate_conversation_history(agent_profile)
        
        # Create memory test points
        for i in range(num_scenarios):
            # Select random memory points from history
            memory_points = random.sample(history, k=3)
            
            # Generate question that requires these memories
            prompt = f"""
            Given this agent profile: {agent_profile}
            And these past conversation points: {memory_points}
            
            Generate a natural user question that would require recalling 
            these specific memories. Include the expected response elements.
            
            Format as JSON:
            {{
                "question": "...",
                "required_memories": [...],
                "expected_elements": [...]
            }}
            """
            
            result = await self.generator.complete(prompt)
            scenario_data = json.loads(result)
            
            scenarios.append(TestScenario(
                id=f"mem_recall_{i}",
                name=f"Memory Recall Test {i}",
                messages=[
                    {"role": "user", "content": scenario_data["question"]}
                ],
                memory_requirements=scenario_data["required_memories"],
                expected_capabilities=["memory_recall", "context_integration"],
                evaluation_criteria={
                    "memory_accuracy": 0.9,
                    "coherence": 0.8
                }
            ))
        
        return scenarios
```

### 2.2 Synthetic Conversation Generator

```python
class ConversationSynthesizer:
    """Generate realistic multi-turn conversations"""
    
    async def generate_conversation_dataset(
        self,
        domains: list[str],
        conversation_length: tuple[int, int] = (5, 20),
        num_conversations: int = 100
    ) -> list[dict]:
        """Generate synthetic conversations for testing"""
        
        conversations = []
        
        for _ in range(num_conversations):
            domain = random.choice(domains)
            length = random.randint(*conversation_length)
            
            # Generate conversation seed
            seed = await self._generate_conversation_seed(domain)
            
            # Build conversation
            messages = [{"role": "system", "content": seed["context"]}]
            
            for turn in range(length):
                # Generate user message
                user_msg = await self._generate_user_turn(
                    messages, 
                    seed["objectives"]
                )
                messages.append({"role": "user", "content": user_msg})
                
                # Generate assistant response
                assistant_msg = await self._generate_assistant_turn(
                    messages,
                    seed["agent_traits"]
                )
                messages.append({"role": "assistant", "content": assistant_msg})
                
                # Inject memory points
                if turn % 3 == 0:
                    memory_point = self._extract_memory_point(messages)
                    seed["memory_points"].append(memory_point)
            
            conversations.append({
                "id": f"synth_conv_{len(conversations)}",
                "domain": domain,
                "messages": messages[1:],  # Exclude system message
                "memory_points": seed["memory_points"],
                "metadata": seed
            })
        
        return conversations
```

### 2.3 Adversarial Test Generator

```python
class AdversarialTestGenerator:
    """Generate challenging edge cases and adversarial examples"""
    
    async def generate_edge_cases(self) -> list[TestScenario]:
        """Generate scenarios that test system boundaries"""
        
        edge_cases = []
        
        # Memory contradiction tests
        edge_cases.extend(await self._generate_memory_contradictions())
        
        # Context overflow tests
        edge_cases.extend(await self._generate_context_overflow())
        
        # Temporal consistency tests
        edge_cases.extend(await self._generate_temporal_tests())
        
        # Multi-agent confusion tests
        edge_cases.extend(await self._generate_multi_agent_confusion())
        
        return edge_cases
    
    async def _generate_memory_contradictions(self) -> list[TestScenario]:
        """Test handling of contradictory memories"""
        
        scenarios = []
        
        # Create contradictory memory pairs
        contradictions = [
            {
                "memory_1": "User's favorite color is blue",
                "memory_2": "User's favorite color is red",
                "question": "What's my favorite color?",
                "expected_handling": "acknowledge_contradiction"
            },
            {
                "memory_1": "User is allergic to peanuts",
                "memory_2": "User loves peanut butter sandwiches",
                "question": "Can you recommend a snack?",
                "expected_handling": "prioritize_safety"
            }
        ]
        
        for i, contradiction in enumerate(contradictions):
            scenarios.append(TestScenario(
                id=f"contradiction_{i}",
                name=f"Memory Contradiction {i}",
                messages=[
                    {"role": "system", "content": f"Memory 1: {contradiction['memory_1']}"},
                    {"role": "system", "content": f"Memory 2: {contradiction['memory_2']}"},
                    {"role": "user", "content": contradiction["question"]}
                ],
                memory_requirements=[
                    contradiction["memory_1"],
                    contradiction["memory_2"]
                ],
                expected_capabilities=["contradiction_handling"],
                evaluation_criteria={
                    "safety": 1.0,
                    "coherence": 0.8,
                    "handling": contradiction["expected_handling"]
                }
            ))
        
        return scenarios
```

## 3. Dataset Augmentation Pipeline

### 3.1 Variation Generator

```python
class DatasetAugmenter:
    """Augment existing datasets with variations"""
    
    def generate_variations(
        self, 
        base_scenario: TestScenario,
        variation_types: list[str]
    ) -> list[TestScenario]:
        """Generate variations of a base scenario"""
        
        variations = []
        
        if "paraphrase" in variation_types:
            variations.extend(self._generate_paraphrases(base_scenario))
        
        if "persona" in variation_types:
            variations.extend(self._generate_persona_shifts(base_scenario))
        
        if "complexity" in variation_types:
            variations.extend(self._generate_complexity_levels(base_scenario))
        
        if "language_style" in variation_types:
            variations.extend(self._generate_style_variations(base_scenario))
        
        return variations
    
    def _generate_paraphrases(self, scenario: TestScenario) -> list[TestScenario]:
        """Generate paraphrased versions of questions"""
        
        paraphraser = pipeline("text2text-generation", 
                              model="humarin/chatgpt_paraphraser_on_T5_base")
        
        variations = []
        for i in range(3):
            paraphrased = paraphraser(
                f"paraphrase: {scenario.messages[-1]['content']}"
            )[0]['generated_text']
            
            new_scenario = copy.deepcopy(scenario)
            new_scenario.id = f"{scenario.id}_para_{i}"
            new_scenario.messages[-1]['content'] = paraphrased
            variations.append(new_scenario)
        
        return variations
```

### 3.2 Cross-Dataset Fusion

```python
class DatasetFusion:
    """Combine multiple datasets into comprehensive test suites"""
    
    def create_hybrid_scenarios(
        self,
        datasets: dict[str, Dataset]
    ) -> list[TestScenario]:
        """Combine elements from multiple datasets"""
        
        hybrid_scenarios = []
        
        # Combine PersonaChat personas with MMLU questions
        personas = datasets["personachat"]["train"]["personality"]
        questions = datasets["mmlu"]["test"]["question"]
        
        for i, (persona, question) in enumerate(zip(personas[:100], questions[:100])):
            scenario = TestScenario(
                id=f"hybrid_persona_knowledge_{i}",
                name=f"Persona + Knowledge Test {i}",
                messages=[
                    {"role": "system", "content": f"You have this persona: {persona}"},
                    {"role": "user", "content": question["text"]}
                ],
                expected_capabilities=["persona_consistency", "knowledge_recall"],
                memory_requirements=persona,
                evaluation_criteria={
                    "persona_adherence": 0.8,
                    "factual_accuracy": 0.9
                }
            )
            hybrid_scenarios.append(scenario)
        
        return hybrid_scenarios
```

## 4. Quality Control Pipeline

### 4.1 Scenario Validator

```python
class ScenarioQualityControl:
    """Validate and score generated scenarios"""
    
    async def validate_scenario_batch(
        self,
        scenarios: list[TestScenario]
    ) -> list[tuple[TestScenario, float]]:
        """Score scenarios for quality and usefulness"""
        
        scored_scenarios = []
        
        for scenario in scenarios:
            score = await self._score_scenario(scenario)
            
            if score > 0.7:  # Quality threshold
                scored_scenarios.append((scenario, score))
        
        return sorted(scored_scenarios, key=lambda x: x[1], reverse=True)
    
    async def _score_scenario(self, scenario: TestScenario) -> float:
        """Score individual scenario quality"""
        
        scores = {
            "clarity": self._score_clarity(scenario),
            "complexity": self._score_complexity(scenario),
            "coverage": self._score_capability_coverage(scenario),
            "realism": await self._score_realism(scenario)
        }
        
        return sum(scores.values()) / len(scores)
```

## 5. Dataset Management System

### 5.1 Dataset Registry

```python
@dataclass
class DatasetRegistry:
    """Central registry for all test datasets"""
    
    datasets: dict[str, TestDataset] = field(default_factory=dict)
    
    def register_huggingface_dataset(
        self,
        name: str,
        hf_dataset_id: str,
        converter: Callable
    ):
        """Register and convert HuggingFace dataset"""
        
        hf_dataset = load_dataset(hf_dataset_id)
        test_scenarios = converter(hf_dataset)
        
        self.datasets[name] = TestDataset(
            id=f"hf_{name}",
            name=name,
            version="1.0",
            created_at=datetime.utcnow(),
            scenarios=test_scenarios,
            baseline_scores={},
            metadata={"source": "huggingface", "hf_id": hf_dataset_id}
        )
    
    def register_synthetic_dataset(
        self,
        name: str,
        generator: Callable,
        size: int = 100
    ):
        """Generate and register synthetic dataset"""
        
        scenarios = asyncio.run(generator(size))
        
        self.datasets[name] = TestDataset(
            id=f"synth_{name}",
            name=name,
            version="1.0",
            created_at=datetime.utcnow(),
            scenarios=scenarios,
            baseline_scores={},
            metadata={"source": "synthetic", "generator": generator.__name__}
        )
```

## 6. Implementation Plan

### Phase 1: Foundation (Week 1)
- Set up HuggingFace dataset loaders
- Implement basic converters for MMLU, PersonaChat
- Create simple synthetic conversation generator

### Phase 2: Expansion (Week 2)
- Add tool usage datasets (ToolBench)
- Implement memory-focused scenario generator
- Add voice dataset integration

### Phase 3: Advanced (Week 3)
- Build adversarial test generator
- Implement dataset augmentation pipeline
- Create quality control system

### Phase 4: Integration (Week 4)
- Build dataset registry and management
- Create automated dataset refresh pipeline
- Implement baseline scoring system

## 7. Recommended Initial Dataset Mix

For PMF testing, start with:

1. **30%** HuggingFace benchmarks (MMLU, PersonaChat)
2. **40%** Synthetic memory/conversation scenarios
3. **20%** Tool usage scenarios
4. **10%** Adversarial/edge cases

This provides broad coverage while focusing on Kairix's unique memory capabilities.