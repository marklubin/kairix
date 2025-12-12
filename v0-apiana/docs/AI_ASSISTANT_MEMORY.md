# AI Assistant Memory

## Session: 2024-01-30

### What We Built
1. **Prefect Workflow Structure**
   - Simplified to just summary generation (no knowledge graph yet)
   - Batch processing with progress callbacks
   - Write to disk before Neo4j

2. **Neo4j Schema with neomodel**
   - ExperientialSummary nodes
   - Vector embeddings for similarity search
   - Contextual tagging (emotional, environmental, activity, social)

3. **Architecture Decisions**
   - Use Ollama for local LLM (summaries + context extraction)
   - Embedding model TBD (considering Ollama or dedicated)
   - Separate knowledge graph extraction for later phase
   - JSON properties for contexts (can migrate to nodes later)

### Current State
- ✅ Project structure created
- ✅ Neo4j schema defined
- ✅ Prefect workflow skeleton
- ✅ Contextual tagging structure
- ⏳ Ollama integration (TODO)
- ⏳ Embedding generation (TODO)
- ⏳ TUI progress tracking (TODO)

### Implementation Notes
- Using `uv` for package management
- Neo4j connection via neomodel ORM
- Conversations already loaded by TUI (no parsing needed)
- First-person experiential summaries

### Next Session Should
1. Implement `OllamaClient` in `export_processor/llm/ollama_client.py`
2. Decide on embedding approach
3. Wire up the actual Prefect tasks
4. Test with sample conversation