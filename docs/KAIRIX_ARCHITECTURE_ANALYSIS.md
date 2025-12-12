# Kairix Architecture Analysis & Refactoring Plan

## Executive Summary

Kairix is a conversational AI system with memory capabilities, built as a monolithic Python application with ~22,000 lines of code. The system provides an OpenAI-compatible API endpoint with a cognitive engine that maintains conversation history, generates insights, and reflects on interactions. While functional, the codebase has significant opportunities for simplification while maintaining its core runtime engine and service layers.

## Current Architecture Overview

### System Components

```
kairix/
├── kairix-core/      (100 Python files, ~10,000 lines)
│   ├── api/          # OpenAI API compatibility layer
│   ├── cognition/    # Persona and perceptor systems
│   ├── runtime/      # Core execution engines
│   ├── embedding/    # Vector embedding support
│   └── database/     # SQLite storage layer
├── kairix-apps/      (16 Python files, ~1,600 lines)
│   ├── engine.py     # Main engine configuration
│   └── server.py     # FastAPI server implementation
├── kairix-offline/   # Offline processing tools
├── kairix-cli/       # CLI management tools
├── kairix-website/   # Web interface (to be replaced)
└── perceptor-inspector/  # Debugging tools
```

### Core Runtime Components (To Preserve)

1. **AgentRuntime** (`runtime/agent.py`)
   - Manages AI agent configuration and execution
   - Handles multiple provider mappings (OpenAI, Ollama, etc.)
   - Singleton pattern for consistent runtime state
   - MCP server integration for external tools

2. **StorageRuntime** (`runtime/storage.py`)
   - SQLite database management with vector search
   - Generic DAO pattern for data access
   - Session management and transaction handling
   - Vector search capabilities via sqlite-vec

3. **LoggingRuntime** (`runtime/logging.py`)
   - Centralized logging configuration
   - File and console output handlers
   - Simple singleton implementation

4. **KairixEngine** (`kairix_apps/engine.py`)
   - Orchestrates persona creation with perceptors
   - Environmental context awareness
   - Conversation history management
   - Incremental reflection system

5. **FastAPI Server** (`kairix_apps/server.py`)
   - OpenAI-compatible REST API
   - Streaming and non-streaming responses
   - Context update endpoints
   - Health monitoring

## Architecture Simplification Plan

### Phase 1: Component Consolidation (Reduce by ~40% LOC)

#### 1.1 Merge Redundant Modules
```python
# Before: 5 separate perceptor files
kairix_core/cognition/perceptor/
├── environmental_context.py
├── incremental_reflection.py
├── sqlite_conversation_history.py
├── summary_insight.py
└── base.py

# After: Single unified perceptor module
kairix_core/perceptors.py  # All perceptors in one file
```

#### 1.2 Simplify Type System
```python
# Before: 15+ type definition files
kairix_core/types/
├── cognition.py
├── db.py
├── environmental_context.py
├── memories.py
└── ... (many more)

# After: 2 consolidated type files
kairix_core/
├── models.py     # All data models
└── interfaces.py # All interfaces/protocols
```

#### 1.3 Remove Unused Features
- Remove kairix-offline module (5,000+ lines)
- Remove kairix-cli module (2,000+ lines)
- Remove kairix-metrics module
- Remove perceptor-inspector module
- Remove kairix-website (being replaced)

### Phase 2: Architectural Refactoring

#### 2.1 Simplified Directory Structure
```
kairix/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── runtime.py      # All runtime classes
│   │   ├── storage.py      # Storage and vector search
│   │   └── logging.py      # Logging configuration
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── persona.py      # Persona and conversation
│   │   ├── perceptors.py   # All perceptor implementations
│   │   └── memory.py       # Memory management
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py       # FastAPI application
│   │   ├── adapters.py     # OpenAI adapter
│   │   └── models.py       # API models
│   └── config.py           # All configuration
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── pyproject.toml
└── README.md
```

#### 2.2 Dependency Reduction
```toml
# Current: 30+ dependencies
# Target: 10-12 core dependencies
[dependencies]
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
sqlalchemy = "^2.0.0"
pydantic = "^2.0.0"
agents = "^0.2.0"  # For AI agent management
openai = "^1.0.0"  # For API compatibility types
httpx = "^0.25.0"  # Async HTTP client
python-dotenv = "^1.0.0"
sqlite-vec = "^0.1.0"  # Vector search
```

### Phase 3: Code Optimization Patterns

#### 3.1 Replace Class Hierarchies with Functions
```python
# Before: Complex class hierarchy
class Perceptor(ABC):
    @abstractmethod
    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        pass

class SummaryInsightPerceptor(Perceptor):
    def __init__(self, runtime, store, k_memories):
        # 50+ lines of initialization

    async def perceive(self, stimulus):
        # 100+ lines of logic

# After: Simple function-based approach
async def perceive_summary_insights(
    stimulus: Stimulus,
    runtime: AgentRuntime,
    k: int = 5
) -> List[Perception]:
    """Generate summary insights from stimulus."""
    # 30-40 lines of focused logic
```

#### 3.2 Consolidate Configuration
```python
# Before: Multiple configuration files and environment variables
# After: Single configuration source
@dataclass
class KairixConfig:
    """Complete system configuration."""
    server_port: int = 8000
    api_key: Optional[str] = None
    model_provider: str = "openai"
    model_name: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000
    sqlite_path: str = "./kairix.db"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "KairixConfig":
        """Load configuration from environment."""
        return cls(
            server_port=int(os.getenv("PORT", 8000)),
            api_key=os.getenv("API_KEY"),
            # ... etc
        )
```

#### 3.3 Streamline Storage Layer
```python
# Before: Generic DAO pattern with 200+ lines
# After: Focused storage interface
class Storage:
    """Simplified storage interface."""

    def __init__(self, db_path: str):
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.Session = sessionmaker(bind=self.engine)

    async def save_message(self, agent_id: str, role: str, content: str):
        """Save a conversation message."""
        # 10-15 lines

    async def get_history(self, agent_id: str, limit: int = 10):
        """Get conversation history."""
        # 10-15 lines

    async def search_similar(self, embedding: List[float], k: int = 5):
        """Vector similarity search."""
        # 15-20 lines
```

### Phase 4: Testing Strategy Overhaul

#### 4.1 E2E Testing Suite
```python
# tests/e2e/test_api_flows.py
class TestAPIFlows:
    """End-to-end API testing."""

    async def test_conversation_flow(self):
        """Test complete conversation with memory."""
        # 1. Start server
        # 2. Send messages
        # 3. Verify responses
        # 4. Check memory persistence

    async def test_streaming_responses(self):
        """Test SSE streaming."""
        # Verify chunk-by-chunk delivery

    async def test_context_updates(self):
        """Test environmental context updates."""
        # Verify context affects responses
```

#### 4.2 Integration Testing
```python
# tests/integration/test_engine.py
async def test_persona_with_perceptors():
    """Test persona creation and perceptor integration."""
    # Test without external dependencies

async def test_memory_persistence():
    """Test memory storage and retrieval."""
    # Use in-memory SQLite for speed
```

#### 4.3 Contract Testing
```python
# tests/contract/test_openai_compatibility.py
def test_api_contract():
    """Verify OpenAI API compatibility."""
    # Test request/response formats
    # Validate against OpenAI schemas
```

## Implementation Roadmap

### Week 1: Foundation
- [ ] Create new simplified directory structure
- [ ] Set up consolidated configuration system
- [ ] Migrate core runtime components
- [ ] Establish testing framework

### Week 2: Consolidation
- [ ] Merge perceptor implementations
- [ ] Simplify type system
- [ ] Consolidate storage layer
- [ ] Remove unused modules

### Week 3: Optimization
- [ ] Replace class hierarchies with functions
- [ ] Implement streamlined API layer
- [ ] Optimize memory management
- [ ] Add performance monitoring

### Week 4: Testing & Documentation
- [ ] Complete E2E test suite
- [ ] Write API documentation
- [ ] Create deployment guide
- [ ] Performance benchmarking

## Expected Outcomes

### Metrics
- **Lines of Code**: 22,000 → ~8,000 (64% reduction)
- **Dependencies**: 30+ → 10-12 (60% reduction)
- **Test Coverage**: 40% → 90%
- **Startup Time**: 5s → <1s
- **Memory Usage**: 500MB → 200MB

### Benefits
1. **Maintainability**: Simpler codebase easier to understand and modify
2. **Performance**: Reduced overhead from simplified architecture
3. **Reliability**: Comprehensive testing ensures stability
4. **Deployment**: Smaller footprint, faster deployment
5. **Development**: Faster iteration cycles

## Principal Engineer Recommendations

### 1. State Management
Replace multiple singleton patterns with a single application context:
```python
@dataclass
class AppContext:
    """Single source of truth for application state."""
    config: KairixConfig
    runtime: AgentRuntime
    storage: Storage
    logger: Logger
```

### 2. Observability
Add structured logging and metrics:
```python
# Use structured logging
logger.info("api_request", method="POST", path="/v1/chat/completions", duration_ms=150)

# Add key metrics
- Request latency histogram
- Token usage counter
- Memory operation duration
- Error rate by endpoint
```

### 3. Error Handling
Implement consistent error handling:
```python
class KairixError(Exception):
    """Base exception with context."""
    def __init__(self, message: str, context: dict = None):
        self.context = context or {}
        super().__init__(message)

# Use specific exceptions
class StorageError(KairixError): pass
class ConfigurationError(KairixError): pass
class ModelProviderError(KairixError): pass
```

### 4. Resource Management
Use context managers for all resources:
```python
async with create_app() as app:
    async with app.storage.session() as session:
        # Automatic cleanup on exit
```

### 5. Development Workflow
```makefile
# Simple Makefile for common tasks
.PHONY: dev test build

dev:
	uvicorn src.api.server:app --reload --port 8000

test:
	pytest tests/ -v --cov=src --cov-report=html

build:
	docker build -t kairix:latest .

format:
	black src/ tests/
	isort src/ tests/
```

### 6. Security Considerations
- Use environment variables for all secrets
- Implement rate limiting on API endpoints
- Add request validation middleware
- Use prepared statements for all SQL queries
- Implement API key rotation mechanism

### 7. Performance Optimizations
- Cache frequently accessed memory summaries
- Use connection pooling for database
- Implement lazy loading for perceptors
- Add request/response compression
- Use async/await consistently

## Conclusion

This refactoring plan maintains the core value of Kairix - its cognitive engine and memory system - while dramatically simplifying the implementation. The focus on a single-user application allows us to remove unnecessary complexity around scaling and multi-tenancy. The simplified architecture will be easier to maintain, test, and extend while providing the same functionality with better performance and reliability.

## Next Steps

1. Review and approve this plan
2. Set up new project structure
3. Begin incremental migration
4. Implement comprehensive testing
5. Deploy simplified version