# TODO: Apiana AI Development Tasks

*Last updated: June 3, 2025*

## High Priority 🔥

### 1. Store Conversations in Better Format
**Status**: Pending  
**Priority**: High

**Current Issues**:
- Basic conversation storage without rich metadata
- Limited relationship modeling in Neo4j
- No conversation threading or temporal relationships

**Improvements Needed**:
- [ ] Add conversation metadata (duration, participant count, topics)
- [ ] Create temporal relationships between conversations
- [ ] Store individual messages as separate nodes with relationships
- [ ] Add conversation threading and context chains
- [ ] Implement better data model for conversation evolution over time

### 2. Semantic Chunking
**Status**: Pending  
**Priority**: High

**Current Issues**:
- Simple token-based chunking loses semantic meaning
- Chunks may split related concepts inappropriately
- No consideration of conversation flow or topic boundaries

**Improvements Needed**:
- [ ] Implement semantic chunking based on topic shifts
- [ ] Use embedding similarity to identify natural breakpoints
- [ ] Preserve conversation context across chunks
- [ ] Add overlap strategies for maintaining coherence
- [ ] Test different chunking strategies (sliding window, topic-based, etc.)

## Medium Priority ⚡

### 3. Parallelize Summarization Calls
**Status**: Pending  
**Priority**: Medium

**Current Issues**:
- Sequential processing is slow for large batches
- Underutilizing available compute resources
- Long processing times for conversation exports

**Improvements Needed**:
- [ ] Implement async/parallel processing for summarization
- [ ] Add batch processing with configurable concurrency
- [ ] Add progress tracking and error handling for parallel jobs
- [ ] Optimize for both local and remote LLM endpoints
- [ ] Add rate limiting and retry logic

### 4. Find More Appropriate Model
**Status**: Pending  
**Priority**: Medium

**Current Issues**:
- 200K context window may still be insufficient for largest conversations (670K tokens)
- Current model may not be optimal for conversation summarization
- Need better long-context handling

**Research Needed**:
- [ ] Test latest long-context models (Claude-3.5, GPT-4 Turbo, Gemini)
- [ ] Evaluate specialized conversation/dialogue models
- [ ] Test models with 1M+ context windows
- [ ] Compare quality vs. cost for different model options
- [ ] Implement model switching based on conversation size

## Implementation Notes

### Current Processing Pipeline
```
ChatGPT Export → Parse → Chunk → Summarize → Embed → Store
```

### Proposed Enhanced Pipeline
```
ChatGPT Export → Parse → Semantic Chunk → Parallel Summarize → 
Enhanced Embed → Rich Store → Index & Relate
```

### Technical Considerations
- **Storage**: Neo4j graph structure needs redesign for richer relationships
- **Chunking**: Consider using sentence-transformers for semantic boundaries
- **Parallelization**: asyncio vs threading vs multiprocessing trade-offs
- **Models**: Balance between context length, quality, and cost
- **Memory**: Large conversations require streaming/batching strategies

### Success Metrics
- [ ] Processing time reduction >50%
- [ ] Better conversation coherence in summaries
- [ ] Successful processing of 670K+ token conversations
- [ ] Rich queryable conversation relationships in Neo4j
- [ ] No loss of important conversation context

---

## Completed ✅

### Setup and Infrastructure
- [x] Created Gradio web UI for ChatGPT export processing
- [x] Implemented long-context model (200K context window)
- [x] Set up remote Ollama server integration
- [x] Created chunking script for oversized conversations
- [x] Established Neo4j connection and basic storage
- [x] Built CLI tools for conversation processing

### Testing and Validation
- [x] Verified Neo4j data storage (20 conversations stored)
- [x] Tested embedding generation and vector storage
- [x] Created debugging and monitoring scripts
- [x] Validated conversation parsing from ChatGPT exports

---

*This TODO list serves as a living document for tracking Apiana AI development progress.*