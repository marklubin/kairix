# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Apiana AI is a comprehensive system for building memory-enabled AI agents. This monorepo contains the reference implementation for creating AI systems with persistent, experiential memory that can remember, reflect, and evolve with users over time.

## Common Development Commands

```bash
# Install dependencies (using uv package manager)
uv sync

# Run the new modular ChatGPT Export CLI (recommended)
uv run chatgpt-export-v2 -i export.json -o output/

# Use local LLM with the CLI
uv run chatgpt-export-v2 -i export.json -o output/ --local-llm microsoft/DialoGPT-small --quantize-4bit

# Run the ChatGPT Export TUI application
uv run chatgpt-export-tui

# Run the Gradio Web UI for pipeline execution
uv run python launch_gradio.py
# Opens web interface at http://localhost:7860

# Run tests
make test              # Unit tests only
make test-integ        # Integration tests
make test-ui           # UI automation tests
make test-comprehensive # All tests with environment checks

# Run linting and auto-fix
uv run ruff check --fix

# Run with hot reload during development
uv run textual run --dev apiana/applications/chatgpt_export/tui.py
```

## Code Architecture

### Module Structure

```
apiana/
├── applications/          # User-facing applications
│   ├── batch/            # Batch processing pipelines
│   ├── chatgpt_export/   # CLI and TUI for ChatGPT exports
│   └── gradio/           # Web UI with automatic pipeline discovery
├── core/                 # Core functionality
│   ├── components/       # Reusable pipeline components
│   ├── pipelines/        # Pipeline system and builder
│   └── providers/        # LLM and embedding providers
├── stores/               # Storage backends
│   └── neo4j/           # Graph storage with vector support
└── types/               # Data models and configurations
```

### Core Components

1. **Pipeline System** (`apiana/core/pipelines/`):
   - Component-based architecture
   - Type validation and compatibility checking
   - Progress tracking and error handling
   - Extensible through factory pattern

2. **Components** (`apiana/core/components/`):
   - Readers: ChatGPTExportReader, TextReader, FragmentListReader
   - Transforms: ValidationTransform, SummarizerTransform, EmbeddingTransform
   - Chunkers: ConversationChunkerComponent
   - Writers: ChatFragmentWriter, MemoryBlockWriter, PipelineRunWriter
   - Managers: PipelineRunManager for execution tracking

3. **Storage Layer** (`apiana/stores/neo4j/`):
   - **ApplicationStore**: Shared storage for ChatFragments and pipeline metadata
   - **AgentMemoryStore**: Agent-specific memories with automatic agent_id tagging
   - Works with Neo4j Community Edition (single database)
   - Vector index support for similarity search

4. **Pipeline Factories** (`pipelines.py`):
   - `chatgpt_full_processing_pipeline`: Complete processing with memory generation
   - `chatgpt_fragment_only_pipeline`: Simple fragment storage
   - `fragment_to_memory_pipeline`: Convert fragments to memories
   - `dummy_test_pipeline`: Safe testing pipeline

5. **Gradio Application** (`apiana/applications/gradio/`):
   - Automatic pipeline discovery from `pipelines.py`
   - Dynamic UI generation based on function signatures
   - Real-time execution progress tracking
   - Custom monochrome theme

### Key Implementation Details

- **Memory Types**: Experiential, Conceptual, Reference, Reflective, Task State
- **Data Models**: Using dataclasses and Neomodel for graph storage
- **Neo4j Support**: Works with Community Edition using agent_id properties
- **Type System**: Strong typing with runtime validation
- **Testing**: Comprehensive unit, integration, and UI automation tests

### Development Notes

- Always use `uv` for package management (not pip)
- Import modules unconditionally at the top of files
- Follow component input/output type specifications
- Neo4j Community Edition is sufficient (no Enterprise features required)
- Run `uv run ruff check --fix` after making changes
- The project uses a component-based pipeline architecture

### Adding New Features

1. **New Pipeline Components**:
   - Inherit from appropriate base class (Component, Reader, Writer, etc.)
   - Define input_types and output_types
   - Implement process() method
   - Add tests in tests/unit/core/components/

2. **New Pipelines**:
   - Add factory function to `pipelines.py`
   - Add metadata to `PIPELINE_REGISTRY`
   - The Gradio UI will automatically discover it

3. **New Storage Backends**:
   - Implement store interface in `apiana/stores/`
   - Ensure agent_id filtering is supported
   - Add appropriate tests

### Testing Strategy

- Unit tests: Test individual components
- Integration tests: Test pipeline workflows
- UI automation tests: Test Gradio interface with Playwright
- Run `make test-comprehensive` before committing

### Future Considerations

- Additional vector database backends (Chroma, Weaviate)
- Multi-agent memory sharing protocols
- Reflection scheduling and automated journaling
- Memory export/import tools
- Enhanced pipeline visualization