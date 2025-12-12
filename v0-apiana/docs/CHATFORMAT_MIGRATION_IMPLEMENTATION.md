# ChatFormat Migration & Architecture Refactoring Plan

## Overview
This document outlines the comprehensive plan to:
1. Migrate from custom Pydantic models to chatformat
2. Refactor architecture to separate business logic from UI
3. Implement modular processing pipeline using neo4j-graphrag patterns
4. Add conversation chunking with 5000 token limit
5. Create local LLM provider using transformers
6. Build comprehensive test suite

## Architecture Design

### Module Structure
```
apiana/
├── core/                      # Business logic (new)
│   ├── __init__.py
│   ├── components/            # Pipeline components
│   │   ├── base.py           # Base component interfaces
│   │   ├── readers.py        # Data input components
│   │   ├── chunkers.py       # Conversation chunking
│   │   ├── processors.py     # LLM/embedding processors
│   │   └── writers.py        # Output components
│   ├── pipelines/            # Pipeline orchestration
│   │   ├── base.py          # Pipeline base class
│   │   ├── chatgpt_export.py # ChatGPT export pipeline
│   │   └── builder.py       # Pipeline builder API
│   ├── providers/            # LLM/embedding providers
│   │   ├── base.py          # Provider interfaces
│   │   ├── openai.py        # OpenAI-compatible provider
│   │   └── local.py         # Local transformers provider
│   └── services/            # High-level services
│       ├── chunking.py      # Token counting & chunking
│       └── export.py        # Export processing service
├── applications/            # UI layer (existing, refactored)
│   ├── chatgpt_export/
│   │   ├── cli.py          # Thin CLI wrapper
│   │   └── tui.py          # Thin TUI wrapper
│   └── gradio_ui.py        # Enhanced with pipeline visualization
└── tests/                   # Comprehensive test suite
    ├── unit/               # Component tests
    ├── integration/        # Pipeline tests
    └── e2e/               # End-to-end tests
```

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)

#### 1.1 Base Component Interfaces
```python
# apiana/core/components/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from dataclasses import dataclass

@dataclass
class ComponentResult:
    """Result from component execution"""
    data: Any
    metadata: Dict[str, Any]
    errors: List[str]

class Component(ABC):
    """Base component interface"""
    
    @abstractmethod
    def process(self, input_data: Any) -> ComponentResult:
        """Process input and return result"""
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Any) -> List[str]:
        """Validate input, return list of errors"""
        pass
```

#### 1.2 Chunking Service
```python
# apiana/core/services/chunking.py
from typing import List, Tuple
from transformers import AutoTokenizer
from apiana.types.chat_fragment import ChatFragment

class ConversationChunker:
    """Chunks conversations respecting token limits"""
    
    def __init__(self, model_name: str, max_tokens: int = 5000):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.max_tokens = max_tokens
    
    def chunk_fragment(self, fragment: ChatFragment) -> List[ChatFragment]:
        """Split fragment into chunks under token limit"""
        # Implementation details...
```

### Phase 2: Processing Components (Week 1-2)

#### 2.1 Reader Components
```python
# apiana/core/components/readers.py
class ChatGPTExportReader(Component):
    """Reads ChatGPT export files"""
    
    def process(self, file_path: str) -> ComponentResult:
        fragments = load(file_path)
        return ComponentResult(
            data=fragments,
            metadata={"count": len(fragments)},
            errors=[]
        )
```

#### 2.2 Processor Components
```python
# apiana/core/components/transform.py
class SummarizerProcessor(Component):
    """Summarizes conversations using LLM"""
    
    def __init__(self, llm_provider):
        self.llm = llm_provider
    
    def process(self, fragments: List[ChatFragment]) -> ComponentResult:
        summaries = []
        for fragment in fragments:
            summary = self.llm.summarize(fragment.to_plain_text())
            summaries.append(summary)
        return ComponentResult(data=summaries, metadata={}, errors=[])
```

#### 2.3 Local LLM Provider
```python
# apiana/core/providers/local.py
from transformers import AutoModelForCausalLM, AutoTokenizer

class LocalTransformersLLM:
    """Local LLM using transformers library"""
    
    def __init__(self, model_name: str, device: str = "auto"):
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    def generate(self, prompt: str, **kwargs) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt")
        outputs = self.model.generate(**inputs, **kwargs)
        return self.tokenizer.decode(outputs[0])
```

### Phase 3: Pipeline System (Week 2)

#### 3.1 Pipeline Builder
```python
# apiana/core/pipelines/builder.py
class PipelineBuilder:
    """Fluent API for building pipelines"""
    
    def __init__(self):
        self.components = []
    
    def add_reader(self, reader: Component) -> 'PipelineBuilder':
        self.components.append(reader)
        return self
    
    def add_chunker(self, chunker: Component) -> 'PipelineBuilder':
        self.components.append(chunker)
        return self
    
    def add_processor(self, processor: Component) -> 'PipelineBuilder':
        self.components.append(processor)
        return self
    
    def build(self) -> Pipeline:
        return Pipeline(self.components)
```

### Phase 4: UI Integration (Week 2-3)

#### 4.1 Refactored CLI
```python
# apiana/applications/chatgpt_export/cli.py
from apiana.core.pipelines.builder import PipelineBuilder
from apiana.core.services.export import ExportService

def main():
    # Simple CLI that delegates to core service
    service = ExportService()
    pipeline = service.create_default_pipeline()
    results = pipeline.run(args.input)
    # Display results...
```

#### 4.2 Enhanced Gradio UI
```python
# apiana/applications/gradio_ui.py
import gradio as gr
from apiana.core.pipelines.builder import PipelineBuilder

def create_pipeline_ui():
    """Create Gradio interface with pipeline visualization"""
    
    with gr.Blocks() as app:
        # File upload
        file_input = gr.File(label="Upload ChatGPT Export")
        
        # Pipeline configuration
        with gr.Row():
            chunking_enabled = gr.Checkbox(label="Enable Chunking", value=True)
            chunk_size = gr.Slider(100, 10000, value=5000, label="Max Tokens")
        
        # Pipeline stages visualization
        with gr.Row():
            stage_1 = gr.Textbox(label="1. Reading", interactive=False)
            stage_2 = gr.Textbox(label="2. Chunking", interactive=False)
            stage_3 = gr.Textbox(label="3. Processing", interactive=False)
            stage_4 = gr.Textbox(label="4. Storage", interactive=False)
        
        # Progress and results
        progress = gr.Progress()
        output = gr.JSON(label="Results")
```

### Phase 5: Testing Strategy (Week 3)

#### 5.1 Unit Tests
```python
# tests/unit/test_chunking.py
def test_chunker_respects_token_limit():
    chunker = ConversationChunker("gpt2", max_tokens=100)
    fragment = ChatFragment(messages=[
        {"role": "user", "content": "Very long message..."},
        {"role": "assistant", "content": "Long response..."}
    ])
    chunks = chunker.chunk_fragment(fragment)
    
    for chunk in chunks:
        token_count = chunker.count_tokens(chunk)
        assert token_count <= 100

def test_chunker_preserves_message_boundaries():
    # Ensure messages aren't split mid-content
    pass
```

#### 5.2 Integration Tests
```python
# tests/integration/test_pipeline.py
def test_chatgpt_export_pipeline():
    pipeline = PipelineBuilder()\
        .add_reader(ChatGPTExportReader())\
        .add_chunker(ConversationChunker("gpt2", 5000))\
        .add_processor(SummarizerProcessor(MockLLM()))\
        .build()
    
    result = pipeline.run("test_export.json")
    assert result.success
    assert len(result.data) > 0
```

#### 5.3 End-to-End Tests
```python
# tests/e2e/test_full_flow.py
def test_full_export_processing():
    # Test with real export file
    # Verify Neo4j stores
    # Check output formats
    pass
```

## Migration Steps

1. **Create new module structure** without breaking existing code
2. **Implement core components** one by one
3. **Add comprehensive tests** for each component
4. **Refactor existing code** to use new components
5. **Update UI layers** to use service classes
6. **Run full test suite** before deployment

## Success Criteria

- [ ] All existing functionality preserved
- [ ] Conversations chunked to 5000 tokens max
- [ ] Local LLM provider working
- [ ] Pipeline system operational
- [ ] Gradio UI shows pipeline progress
- [ ] 90%+ test coverage
- [ ] Performance equal or better than current
- [ ] Clean separation of concerns

## Risks & Mitigations

1. **Breaking existing functionality**
   - Mitigation: Keep old code until new is tested
   - Run parallel testing

2. **Performance degradation**
   - Mitigation: Profile before/after
   - Optimize critical paths

3. **Complex dependencies**
   - Mitigation: Clear interfaces
   - Dependency injection

## Timeline

- Week 1: Core infrastructure & chunking
- Week 2: Components & pipeline system
- Week 3: UI integration & testing
- Week 4: Migration & deployment