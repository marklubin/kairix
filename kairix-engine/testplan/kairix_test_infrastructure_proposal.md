# Kairix Engine Performance & Functional Testing Infrastructure Proposal

## Executive Summary

This proposal outlines a comprehensive testing infrastructure for the Kairix Engine, focusing on performance metrics (Time to First Byte for text/audio), functional evaluation of AI responses, and automated CI/CD integration. The system will enable rapid iteration and data-driven optimization during the prototype phase.

## 1. Architecture Overview

### 1.1 Core Components

```
kairix-test-infrastructure/
├── performance/
│   ├── ttfb_monitor.py      # Time to First Byte measurements
│   ├── audio_latency.py     # Audio response timing
│   └── config_matrix.py     # Configuration variation engine
├── functional/
│   ├── evaluator.py         # Response quality assessment
│   ├── scenarios/           # Test scenarios and use cases
│   └── scoring/             # Scoring engines
├── data/
│   ├── test_sets/           # Shareable test datasets
│   └── results/             # Test results storage
├── api/
│   ├── mock_openai.py       # OpenAI-compatible test API
│   └── config_override.py   # Configuration injection
└── ci/
    ├── github_action.yml    # GitHub Actions workflow
    └── local_runner.py      # Local test execution
```

## 2. Performance Testing Module

### 2.1 Time to First Byte (TTFB) Monitoring

```python
class TTFBMonitor:
    """Measures time to first byte for text and audio responses"""
    
    def __init__(self, api_client: KairixTestClient):
        self.client = api_client
        self.metrics = []
    
    async def measure_text_ttfb(self, prompt: str, config: dict) -> float:
        """Measure TTFB for text streaming responses"""
        start_time = time.perf_counter()
        
        async for chunk in self.client.chat_completion_stream(
            messages=[{"role": "user", "content": prompt}],
            config_overrides=config
        ):
            if chunk.choices[0].delta.content:
                ttfb = time.perf_counter() - start_time
                self.metrics.append({
                    "type": "text",
                    "ttfb": ttfb,
                    "config": config,
                    "timestamp": datetime.utcnow()
                })
                return ttfb
    
    async def measure_audio_ttfb(self, audio_input: bytes, config: dict) -> float:
        """Measure TTFB for voice responses"""
        start_time = time.perf_counter()
        
        async for audio_chunk in self.client.voice_completion_stream(
            audio_data=audio_input,
            config_overrides=config
        ):
            if audio_chunk.data:
                ttfb = time.perf_counter() - start_time
                self.metrics.append({
                    "type": "audio",
                    "ttfb": ttfb,
                    "config": config,
                    "timestamp": datetime.utcnow()
                })
                return ttfb
```

### 2.2 Configuration Matrix Testing

```python
class ConfigurationMatrix:
    """Manages configuration variations for A/B testing"""
    
    DEFAULT_VARIATIONS = {
        "model": ["gpt-4", "gpt-3.5-turbo", "claude-3"],
        "temperature": [0.0, 0.7, 1.0],
        "memory_retrieval": ["vector", "graph", "hybrid"],
        "memory_limit": [10, 50, 100],
        "voice_engine": ["elevenlabs", "azure", "google"],
        "streaming": [True, False]
    }
    
    def generate_test_matrix(self, variations: dict = None) -> list[dict]:
        """Generate all configuration combinations"""
        variations = variations or self.DEFAULT_VARIATIONS
        keys = list(variations.keys())
        values = list(variations.values())
        
        for combo in itertools.product(*values):
            yield dict(zip(keys, combo))
```

## 3. Functional Evaluation Module

### 3.1 Scenario-Based Testing

```python
@dataclass
class TestScenario:
    """Defines a test scenario with expected outcomes"""
    id: str
    name: str
    description: str
    messages: list[dict]
    expected_capabilities: list[str]
    memory_requirements: list[str]
    evaluation_criteria: dict
    
class ScenarioEvaluator:
    """Evaluates AI responses against defined scenarios"""
    
    def __init__(self, evaluator_model: str = "gpt-4"):
        self.evaluator = OpenAI(model=evaluator_model)
        self.scoring_engines = {
            "intelligence": IntelligenceScorer(),
            "memory": MemoryRecallScorer(),
            "style": StyleScorer(),
            "aesthetics": AestheticsScorer()
        }
    
    async def evaluate_scenario(
        self, 
        scenario: TestScenario, 
        response: str,
        context: dict
    ) -> EvaluationResult:
        """Run comprehensive evaluation on a response"""
        
        scores = {}
        
        # General intelligence scoring
        scores["intelligence"] = await self.scoring_engines["intelligence"].score(
            prompt=scenario.messages[-1]["content"],
            response=response,
            expected_capabilities=scenario.expected_capabilities
        )
        
        # Memory accuracy scoring
        scores["memory"] = await self.scoring_engines["memory"].score(
            response=response,
            required_memories=scenario.memory_requirements,
            agent_memory_state=context.get("memory_state")
        )
        
        # Style and aesthetics
        scores["style"] = await self.scoring_engines["style"].score(
            response=response,
            target_style=scenario.evaluation_criteria.get("style")
        )
        
        scores["aesthetics"] = await self.scoring_engines["aesthetics"].score(
            response=response,
            criteria=scenario.evaluation_criteria.get("aesthetics")
        )
        
        return EvaluationResult(
            scenario_id=scenario.id,
            scores=scores,
            raw_response=response,
            timestamp=datetime.utcnow()
        )
```

### 3.2 Scoring Engines

```python
class IntelligenceScorer:
    """Evaluates general intelligence and reasoning"""
    
    async def score(
        self, 
        prompt: str, 
        response: str, 
        expected_capabilities: list[str]
    ) -> float:
        """Score response based on demonstrated intelligence"""
        
        evaluation_prompt = f"""
        Evaluate this AI response for intelligence and reasoning.
        
        User prompt: {prompt}
        AI response: {response}
        
        Expected capabilities: {', '.join(expected_capabilities)}
        
        Score from 0-1 based on:
        - Reasoning quality
        - Problem-solving approach
        - Understanding of nuance
        - Appropriate use of knowledge
        
        Return only a float score.
        """
        
        result = await self.evaluator.complete(evaluation_prompt)
        return float(result.strip())

class MemoryRecallScorer:
    """Evaluates memory retrieval accuracy"""
    
    async def score(
        self,
        response: str,
        required_memories: list[str],
        agent_memory_state: dict
    ) -> dict:
        """Score memory recall accuracy and relevance"""
        
        scores = {
            "recall_accuracy": 0.0,
            "relevance": 0.0,
            "integration": 0.0
        }
        
        # Check for required memory elements
        found_memories = 0
        for memory in required_memories:
            if memory.lower() in response.lower():
                found_memories += 1
        
        scores["recall_accuracy"] = found_memories / len(required_memories)
        
        # Evaluate relevance and integration
        # (Implementation details omitted for brevity)
        
        return scores
```

## 4. Test Data Management

### 4.1 Shareable Dataset Format

```python
@dataclass
class TestDataset:
    """Shareable test dataset format"""
    
    id: str
    name: str
    version: str
    created_at: datetime
    scenarios: list[TestScenario]
    baseline_scores: dict[str, float]
    metadata: dict
    
    def to_json(self) -> str:
        """Export dataset to shareable JSON format"""
        return json.dumps(asdict(self), default=str, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TestDataset':
        """Import dataset from JSON"""
        data = json.loads(json_str)
        return cls(**data)
    
    def to_training_format(self) -> list[dict]:
        """Convert to format suitable for fine-tuning"""
        training_data = []
        
        for scenario in self.scenarios:
            for i, message in enumerate(scenario.messages):
                if message["role"] == "assistant":
                    training_data.append({
                        "messages": scenario.messages[:i+1],
                        "metadata": {
                            "scenario_id": scenario.id,
                            "expected_scores": scenario.evaluation_criteria
                        }
                    })
        
        return training_data
```

## 5. API Integration

### 5.1 OpenAI-Compatible Test API

```python
class KairixTestClient:
    """OpenAI-compatible client with configuration overrides"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session = aiohttp.ClientSession()
    
    async def chat_completion_stream(
        self,
        messages: list[dict],
        config_overrides: dict = None,
        **kwargs
    ):
        """Stream chat completions with config overrides"""
        
        payload = {
            "messages": messages,
            "stream": True,
            **kwargs
        }
        
        if config_overrides:
            payload["config_overrides"] = config_overrides
        
        async with self.session.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"}
        ) as response:
            async for line in response.content:
                if line.startswith(b"data: "):
                    yield json.loads(line[6:])
```

## 6. GitHub Actions Integration

### 6.1 Workflow Configuration

```yaml
name: Kairix Performance & Functional Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 */4 * * *'  # Every 4 hours
  workflow_dispatch:
    inputs:
      config_variations:
        description: 'JSON config variations to test'
        required: false

jobs:
  performance-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        test-type: [text-ttfb, audio-ttfb, tool-usage]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      
      - name: Run performance tests
        env:
          KAIRIX_API_KEY: ${{ secrets.KAIRIX_API_KEY }}
          KAIRIX_TEST_ENDPOINT: ${{ secrets.KAIRIX_TEST_ENDPOINT }}
        run: |
          uv run python -m kairix_test.performance.runner \
            --test-type ${{ matrix.test-type }} \
            --variations '${{ github.event.inputs.config_variations || '{}' }}' \
            --output results/performance-${{ matrix.test-type }}.json
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: results/
  
  functional-tests:
    runs-on: ubuntu-latest
    needs: performance-tests
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Download test datasets
        run: |
          mkdir -p data/test_sets
          curl -L ${{ secrets.TEST_DATASET_URL }} -o data/test_sets/core.json
      
      - name: Run functional evaluation
        env:
          KAIRIX_API_KEY: ${{ secrets.KAIRIX_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          uv run python -m kairix_test.functional.runner \
            --dataset data/test_sets/core.json \
            --output results/functional-scores.json
      
      - name: Generate report
        run: |
          uv run python -m kairix_test.reporting.generator \
            --performance results/performance-*.json \
            --functional results/functional-scores.json \
            --output report.html
      
      - name: Comment PR with results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('report.html', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });
```

## 7. Local Development Runner

```python
class LocalTestRunner:
    """Run tests locally with live monitoring"""
    
    def __init__(self, config_path: str = ".kairix-test.yml"):
        self.config = self._load_config(config_path)
        self.dashboard = TestDashboard()  # Rich/Textual UI
    
    async def run_interactive(self):
        """Run tests with interactive dashboard"""
        
        # Start dashboard
        await self.dashboard.start()
        
        # Run performance tests
        perf_task = asyncio.create_task(
            self._run_performance_suite()
        )
        
        # Run functional tests
        func_task = asyncio.create_task(
            self._run_functional_suite()
        )
        
        # Update dashboard in real-time
        while not all([perf_task.done(), func_task.done()]):
            metrics = await self._collect_metrics()
            await self.dashboard.update(metrics)
            await asyncio.sleep(1)
        
        # Show final results
        await self.dashboard.show_summary(
            performance=await perf_task,
            functional=await func_task
        )
```

## 8. Extension Points

### 8.1 Tool Usage Testing

```python
class ToolUsageEvaluator:
    """Evaluate tool calling capabilities"""
    
    async def evaluate_tool_scenario(
        self,
        scenario: ToolScenario,
        client: KairixTestClient
    ) -> ToolEvaluation:
        """Test tool usage patterns"""
        
        response = await client.chat_completion(
            messages=scenario.messages,
            tools=scenario.available_tools
        )
        
        # Evaluate tool calls
        correct_tools = self._check_tool_selection(
            expected=scenario.expected_tools,
            actual=response.tool_calls
        )
        
        # Evaluate parameters
        correct_params = self._check_tool_parameters(
            expected=scenario.expected_parameters,
            actual=response.tool_calls
        )
        
        return ToolEvaluation(
            correct_selection=correct_tools,
            correct_parameters=correct_params,
            execution_order=self._check_execution_order(response.tool_calls)
        )
```

### 8.2 Voice I/O Testing

```python
class VoiceTestingModule:
    """Test voice input/output capabilities"""
    
    async def test_voice_pipeline(
        self,
        audio_samples: list[AudioSample],
        config: dict
    ) -> VoiceMetrics:
        """End-to-end voice testing"""
        
        metrics = VoiceMetrics()
        
        for sample in audio_samples:
            # Test STT accuracy
            transcription = await self.stt_test(sample.audio, config)
            metrics.stt_accuracy.append(
                self._calculate_wer(sample.transcript, transcription)
            )
            
            # Test voice response
            start = time.perf_counter()
            audio_response = await self.client.voice_completion(
                audio_data=sample.audio,
                config_overrides=config
            )
            
            metrics.voice_ttfb.append(time.perf_counter() - start)
            
            # Test TTS quality
            metrics.tts_quality.append(
                await self._evaluate_tts_quality(audio_response)
            )
        
        return metrics
```

## 9. Implementation Roadmap

### Phase 1: MVP (Weeks 1-2)
- Basic TTFB monitoring for text responses
- Simple functional evaluation with 5-10 scenarios
- Local runner with CLI output
- Basic GitHub Action workflow

### Phase 2: Enhanced Testing (Weeks 3-4)
- Audio/voice testing capabilities
- Configuration matrix testing
- Interactive dashboard for local development
- Expanded scenario library (25+ scenarios)

### Phase 3: Advanced Features (Weeks 5-6)
- Tool usage evaluation
- Memory recall scoring
- Shareable dataset format
- Training data export
- Automated regression detection

## 10. Success Metrics

- **Performance**: <500ms TTFB for text, <1s for audio
- **Functional**: >0.8 average score across all categories
- **Coverage**: 100% of core use cases tested
- **Automation**: <5 minute feedback loop on PRs
- **Insights**: Clear correlation between config changes and metrics

This infrastructure will enable rapid iteration during the prototype phase while building a foundation for production-scale testing and optimization.