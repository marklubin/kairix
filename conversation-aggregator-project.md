# Conversation History Aggregator Project

## Context
Building a bespoke tool to aggregate and analyze conversational history across multiple AI platforms and formats.

## Current State
- **Existing work**: Built a proxy layer with custom logic on top of OpenAI API
  - Supports some aspects but limited in scope
  - Need to expand functionality

## Goal
Create a comprehensive system that:
1. Aggregates conversation history from multiple sources
2. Supports diverse formats:
   - Anthropic (Claude Code JSONL format)
   - OpenAI/ChatGPT
   - Custom formats
3. Enables conversational AI-powered analysis and querying across all history

## Technical Requirements

### Sources to Support
- **Anthropic/Claude Code**: `~/.claude/history.jsonl` format
- **OpenAI/ChatGPT**: Their conversation export format
- **Custom formats**: Various proprietary/custom conversation logs

### Proposed Architecture

```
┌─────────────────────────────────────────────────┐
│           Ingestion Layer (Custom)              │
├─────────────────────────────────────────────────┤
│  • Anthropic JSONL parser                       │
│  • OpenAI format parser                         │
│  • Custom format parsers (extensible)           │
│  • Normalize to unified schema                  │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│            Storage Layer                        │
├─────────────────────────────────────────────────┤
│  • Vector DB (Qdrant/Chroma)                    │
│    - Semantic search across conversations       │
│  • Relational DB (SQLite/Postgres)              │
│    - Metadata, timestamps, platform info        │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│          Query Interface                        │
├─────────────────────────────────────────────────┤
│  Option A: Khoj (conversational queries)        │
│  Option B: Custom MCP server for Claude Code    │
│  Option C: Extend existing OpenAI proxy         │
└─────────────────────────────────────────────────┘
```

### Unified Schema (Proposed)
```python
{
  "id": "uuid",
  "timestamp": 1234567890,  # unix timestamp
  "platform": "anthropic|openai|custom",
  "conversation_id": "...",
  "role": "user|assistant|system",
  "content": "...",
  "metadata": {
    "model": "...",
    "project": "...",
    "custom_fields": {...}
  },
  "embedding": [...]  # vector for semantic search
}
```

## Why Build Custom vs Use Existing Tools

### Existing Tools Evaluated
- **Khoj**: Good for querying, not built for multi-format ingestion
- **PyGPT**: Single-platform focused
- **Open WebUI**: Buggy, complex, not designed for cross-platform aggregation
- **Jan.ai**: Limited scope

### Advantages of Custom Build
✅ Full control over format normalization (critical for mixed sources)
✅ Extensible parser system for new formats
✅ Semantic search across ALL conversation history
✅ Can integrate with existing OpenAI proxy work
✅ Export/analyze in any format needed

## Next Steps

### Phase 1: Enhance Existing Proxy
- Extend current OpenAI proxy to support conversation logging
- Add Anthropic API support
- Implement unified conversation storage

### Phase 2: Build Ingestion Pipeline
- Parser for Claude Code `history.jsonl` format
- Parser for OpenAI conversation exports
- Normalization to unified schema
- Batch ingestion scripts

### Phase 3: Vector Embedding & Search
- Implement sentence-transformers for embeddings
- Set up Qdrant or Chroma vector DB
- Build semantic search capability

### Phase 4: Query Interface
- Decide: Extend proxy, use Khoj, or build custom MCP server
- Implement conversational query interface
- Add filtering (by date, platform, project, etc.)

## Questions to Address

1. **Scope of existing proxy**: What functionality does it currently support?
2. **Primary use case**: What types of queries/analysis are most important?
3. **Data volume**: How many conversations/messages to index initially?
4. **Privacy**: Self-hosted only, or cloud components acceptable?
5. **Interface preference**: Command-line, web UI, or integrated into Claude Code?

## Technical Stack (Tentative)

**Backend**:
- Python (aligns with existing proxy)
- FastAPI or Flask (if extending proxy)
- SQLAlchemy (ORM for relational data)

**Vector/Search**:
- Qdrant (easiest self-hosted vector DB)
- sentence-transformers (embeddings)

**Query Interface**:
- TBD based on use case preference

## Resources & References

- Claude Code history location: `~/.claude/history.jsonl`
- Existing proxy code: [location TBD]
- Khoj: https://github.com/khoj-ai/khoj
- PyGPT: [repo TBD]

## Status
🟡 **Planning Phase** - Ready to continue development when resuming conversation

---

*Created: 2025-10-14*
*Next session: Continue with technical design decisions and implementation planning*
