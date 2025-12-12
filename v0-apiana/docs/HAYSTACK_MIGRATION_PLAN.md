# Haystack Migration Plan for Apiana AI

## Current Project State

### Problem Statement
The current Gradio UI implementation has tightly coupled processing logic with UI components. We need to:
1. Extract processing logic from the UI layer
2. Make each processing step atomic and composable
3. Add idempotency without external dependencies
4. Keep the solution lightweight for prototyping

### Current Implementation Issues
- Processing logic is embedded in Gradio event handlers
- No built-in caching or idempotency
- Difficult to test individual processing steps
- No clear separation between UI and business logic

## Proposed Haystack Migration

### Why Haystack?
- **Built-in pipeline management**: Handles component orchestration automatically
- **Native caching support**: No need to build custom idempotency solutions
- **Component isolation**: Each processing step is a separate, testable component
- **Production-ready**: Includes streaming, batching, async support
- **Extensible**: Easy to add new components or modify existing ones

### Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Gradio UI     │────▶│ Haystack Pipeline│────▶│   Neo4j Store   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │
         │                       ├── Parser Component
         │                       ├── Summarizer Component  
         │                       ├── Embedder Component
         │                       └── Writer Component
         │
         ├── Full Pipeline Tab
         ├── Parser Only Tab
         ├── Summarizer Only Tab
         └── Pipeline Info Tab
```

## Implementation Plan

### Phase 1: Create Custom Haystack Components

#### 1.1 ChatGPTExportParser Component
```python
@component
class ChatGPTExportParser:
    """Parse ChatGPT export file into Documents"""
    
    @component.output_types(documents=List[Document])
    def run(self, file_path: str) -> Dict[str, List[Document]]
```

**Responsibilities:**
- Load ChatGPT export JSON file
- Convert each conversation to Haystack Document format
- Preserve metadata (title, message count, conversation ID)
- Output list of Document objects

#### 1.2 ConversationSummarizer Component
```python
@component  
class ConversationSummarizer:
    """Generate summaries using LLM"""
    
    def __init__(self, llm_client, prompt_template: str = None)
```

**Responsibilities:**
- Accept Document objects with conversation content
- Generate summaries using configured LLM
- Add summaries to document metadata
- Support custom prompt templates

#### 1.3 Neo4jMemoryWriter Component
```python
@component
class Neo4jMemoryWriter:
    """Write documents to Neo4j as memory blocks"""
    
    def __init__(self, neo4j_store)
```

**Responsibilities:**
- Extract conversation data from Documents
- Store conversations, summaries, and embeddings in Neo4j
- Return node IDs for stored data
- Handle Neo4j connection and transactions

### Phase 2: Pipeline Configuration

#### 2.1 Basic Pipeline
```python
def create_chatgpt_processing_pipeline(llm_client, neo4j_store):
    pipeline = Pipeline()
    
    # Add components
    pipeline.add_component("parser", ChatGPTExportParser())
    pipeline.add_component("summarizer", ConversationSummarizer(llm_client))
    pipeline.add_component("embedder", SentenceTransformersDocumentEmbedder())
    pipeline.add_component("neo4j_writer", Neo4jMemoryWriter(neo4j_store))
    
    # Connect components
    pipeline.connect("parser.documents", "summarizer.documents")
    pipeline.connect("summarizer.documents", "embedder.documents")
    pipeline.connect("embedder.documents", "neo4j_writer.documents")
    
    return pipeline
```

#### 2.2 Cached Pipeline
```python
def create_cached_pipeline(llm_client, neo4j_store, cache_dir="./pipeline_cache"):
    pipeline = create_chatgpt_processing_pipeline(llm_client, neo4j_store)
    
    # Enable caching for expensive components
    pipeline.set_cache(
        cache_dir=cache_dir,
        components=["summarizer", "embedder"]
    )
    
    return pipeline
```

### Phase 3: Gradio UI Integration

#### 3.1 HaystackGradioUI Class
- Wraps Haystack pipeline
- Provides access to individual components
- Maintains existing UI tabs and functionality

#### 3.2 Component Access Methods
- `run_full_pipeline()`: Execute complete pipeline
- `run_parser_only()`: Parse without processing
- `run_summarizer_only()`: Summarize manual input
- Component introspection for debugging

### Phase 4: Migration Steps

1. **Install Haystack**
   ```bash
   uv add haystack-ai
   ```

2. **Create component module**
   - `apiana/haystack_components/chatgpt_components.py`

3. **Create pipeline module**
   - `apiana/pipelines/chatgpt_export_pipeline.py`

4. **Update Gradio UI**
   - `apiana/applications/haystack_gradio_ui.py`

5. **Update launch script**
   - Modify `launch_ui.py` to use Haystack UI

6. **Testing**
   - Unit tests for each component
   - Integration tests for full pipeline
   - UI smoke tests

## Benefits of Migration

### Immediate Benefits
1. **Automatic caching**: No custom idempotency code needed
2. **Component isolation**: Each step can be tested independently
3. **Clear separation**: UI logic separated from processing logic
4. **Built-in features**: Logging, metrics, error handling included

### Future Benefits
1. **Easy scaling**: Can add distributed processing later
2. **Pipeline variations**: Easy to create alternative pipelines
3. **Component reuse**: Components can be used in other contexts
4. **Integration ready**: Can integrate with other Haystack components

## Configuration Management

### Pipeline Configuration
```yaml
# config/pipeline.yaml
pipeline:
  cache_dir: "./pipeline_cache"
  components:
    parser:
      type: "ChatGPTExportParser"
    summarizer:
      type: "ConversationSummarizer"
      model: "gpt-4"
      prompt_template: "prompts/summary_prompt.txt"
    embedder:
      type: "SentenceTransformersDocumentEmbedder"
      model: "sentence-transformers/all-MiniLM-L6-v2"
    writer:
      type: "Neo4jMemoryWriter"
      batch_size: 100
```

## Rollback Plan

If issues arise during migration:
1. Keep existing implementation in parallel
2. Add feature flag to switch between implementations
3. Gradual rollout with specific test files
4. Monitor performance and accuracy metrics

## Success Criteria

1. **Functional parity**: All existing features work
2. **Performance**: Similar or better processing times
3. **Caching works**: Repeated runs are faster
4. **Testing**: All components have unit tests
5. **Documentation**: Clear docs for adding new components

## Timeline Estimate

- Phase 1 (Components): 2-3 hours
- Phase 2 (Pipeline): 1-2 hours  
- Phase 3 (UI Integration): 2-3 hours
- Phase 4 (Migration & Testing): 2-3 hours

Total: 1-2 days of development

## Next Steps

1. Confirm approach with team
2. Install Haystack dependencies
3. Create proof-of-concept with single component
4. Implement full pipeline
5. Update UI and test
6. Document component creation process