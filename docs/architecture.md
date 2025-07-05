# Kairix Architecture Overview

This document provides a comprehensive overview of Kairix's system architecture, design principles, and technical implementation.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Applications                     │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │  Web Client │  │   CLI Tool  │  │  Voice Interface │   │
│  └──────┬──────┘  └──────┬──────┘  └────────┬─────────┘   │
└─────────┼────────────────┼──────────────────┼──────────────┘
          │                │                  │
          ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway (FastAPI)                    │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐    │
│  │  REST API  │  │  WebSocket   │  │  Authentication │    │
│  └──────┬─────┘  └──────┬───────┘  └────────┬────────┘    │
└─────────┼───────────────┼──────────────────┼──────────────┘
          │               │                  │
          ▼               ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      Core Engine                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │Agent Runtime│  │  Perceptors  │  │ Memory Manager  │   │
│  └──────┬──────┘  └──────┬───────┘  └────────┬────────┘   │
└─────────┼────────────────┼──────────────────┼──────────────┘
          │                │                  │
          ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   Neo4j DB  │  │ Vector Store │  │  LLM Providers │   │
│  └─────────────┘  └──────────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. API Layer (`kairix-apps`)

**FastAPI Server**
- OpenAI-compatible REST API
- WebSocket support for streaming
- Authentication middleware
- Request validation and routing

**Key Endpoints**
```python
/v1/chat/completions     # Chat with agents
/v1/agents               # Agent management
/v1/memories             # Memory operations
/v1/context/update       # Context updates
/health                  # Health checks
```

### 2. Agent Runtime (`kairix-core/runtime`)

**Singleton Architecture**
```python
class AgentRuntimeSingleton:
    """Manages all active agents and their lifecycle"""
    
    def get_agent(self, agent_id: str) -> Agent
    def create_agent(self, config: AgentConfig) -> Agent
    def update_context(self, agent_id: str, context: Dict)
```

**Agent Lifecycle**
1. Configuration loading
2. Memory store initialization
3. Perceptor registration
4. Persona assignment
5. Active session management

### 3. Cognition System (`kairix-core/cognition`)

**Stimulus-Perception-Action Model**

```python
class CognitionEngine:
    def process_stimulus(self, stimulus: Stimulus) -> Action:
        # 1. Perceptors create perceptions
        perceptions = self.perceive(stimulus)
        
        # 2. Memory provides context
        context = self.memory.retrieve_relevant(perceptions)
        
        # 3. Proposers generate options
        proposals = self.propose(perceptions, context)
        
        # 4. Persona selects action
        action = self.persona.select(proposals)
        
        return action
```

### 4. Memory System (`kairix-core/cognition/stores`)

**Memory Architecture**

```python
class MemoryStore:
    def store(self, memory: Memory) -> str
    def retrieve(self, query: str, limit: int) -> List[Memory]
    def search_semantic(self, embedding: List[float]) -> List[Memory]
    def update_importance(self, memory_id: str, importance: float)
```

**Storage Strategy**
- Graph structure in Neo4j
- Vector embeddings for semantic search
- Temporal indexing for chronological access
- Importance scoring for relevance

### 5. Perceptor System

**Base Perceptor Interface**
```python
class BasePerceptor(ABC):
    @abstractmethod
    async def perceive(self, stimulus: Stimulus) -> Perception:
        pass
```

**Core Perceptors**
- `ConversationHistoryPerceptor`: Dialog context
- `EnvironmentalContextPerceptor`: External conditions
- `SemanticGraphPerceptor`: Entity relationships
- `EmotionalStatePerceptor`: Sentiment tracking
- `TaskProgressPerceptor`: Goal monitoring

### 6. Provider System (`kairix-core/inference`)

**Provider Abstraction**
```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages: List[Message]) -> Response:
        pass
```

**Supported Providers**
- OpenAI (GPT-3.5, GPT-4)
- Ollama (local models)
- llama.cpp (direct inference)
- Custom providers via adapter

## Data Flow

### 1. Request Processing

```
User Input → API Gateway → Validation → Agent Selection → 
Cognition Engine → Memory Context → LLM Provider → 
Response Generation → Streaming/Return
```

### 2. Memory Formation

```
Conversation → Experience Extraction → Embedding Generation →
Importance Scoring → Graph Storage → Index Update →
Consolidation Queue
```

### 3. Reflection Process

```
Schedule Trigger → Memory Collection → Pattern Analysis →
Insight Generation → Reflective Memory Creation →
Knowledge Update
```

## Database Schema

### Neo4j Graph Structure

**Node Types**
```cypher
// Agent Node
(:Agent {
    id: string,
    name: string,
    created_at: datetime,
    config: json
})

// Memory Node
(:Memory {
    id: string,
    agent_id: string,
    type: string,
    content: string,
    embedding: list<float>,
    importance: float,
    timestamp: datetime
})

// Entity Node
(:Entity {
    id: string,
    name: string,
    type: string,
    properties: json
})
```

**Relationships**
```cypher
(agent:Agent)-[:HAS_MEMORY]->(memory:Memory)
(memory:Memory)-[:REFERENCES]->(entity:Entity)
(memory:Memory)-[:RELATED_TO]->(memory:Memory)
(entity:Entity)-[:RELATES_TO]->(entity:Entity)
```

### Vector Indexing

```cypher
CREATE VECTOR INDEX memory_embeddings IF NOT EXISTS
FOR (m:Memory) 
ON m.embedding
OPTIONS {indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
}}
```

## Deployment Architecture

### Containerized Deployment

```yaml
services:
  neo4j:
    image: neo4j:5.15
    environment:
      - NEO4J_AUTH=neo4j/password
    volumes:
      - neo4j_data:/data
    
  backend:
    build: .
    depends_on:
      - neo4j
    environment:
      - NEO4J_URI=bolt://neo4j:7687
    
  frontend:
    build: ./kairix-apps/client
    depends_on:
      - backend
```

### Scaling Considerations

**Horizontal Scaling**
- Stateless API servers
- Shared Neo4j cluster
- Load balancer distribution
- Session affinity for WebSockets

**Vertical Scaling**
- Memory for agent caches
- CPU for embedding generation
- GPU for local models
- Storage for growing memories

## Security Architecture

### Authentication Flow

```
Client → API Key → JWT Generation → Request Authorization →
Role-Based Access → Agent Isolation → Response
```

### Data Isolation

- Agent memories isolated by `agent_id`
- User-specific API keys
- Encrypted storage at rest
- TLS for data in transit

## Performance Optimizations

### Caching Strategy

1. **Agent Cache**: Active agents in memory
2. **Memory Cache**: Recent memories for fast access
3. **Embedding Cache**: Computed embeddings
4. **Response Cache**: Common query patterns

### Query Optimization

```python
# Efficient memory retrieval
MATCH (a:Agent {id: $agent_id})-[:HAS_MEMORY]->(m:Memory)
WHERE m.timestamp > datetime() - duration('P7D')
AND m.importance > 0.7
RETURN m
ORDER BY m.importance DESC, m.timestamp DESC
LIMIT 20
```

### Batch Processing

- Bulk memory insertions
- Parallel embedding generation
- Async perceptor execution
- Stream processing for large exports

## Monitoring & Observability

### Metrics Collection

```python
# Prometheus metrics
request_duration = Histogram('request_duration_seconds')
memory_operations = Counter('memory_operations_total')
active_agents = Gauge('active_agents')
```

### Logging Structure

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "agent_id": "agent-123",
  "user_id": "user-456",
  "action": "chat_completion",
  "duration_ms": 245,
  "memory_count": 5,
  "model": "gpt-4"
}
```

### Health Checks

- Database connectivity
- Memory availability
- Provider status
- Queue depths
- Response times

## Extension Points

### Custom Perceptors

```python
class WeatherPerceptor(BasePerceptor):
    async def perceive(self, stimulus: Stimulus) -> Perception:
        weather = await self.fetch_weather()
        return Perception(
            type="environmental",
            content=f"Current weather: {weather}",
            confidence=0.95
        )
```

### Custom Providers

```python
class CustomLLMProvider(BaseLLMProvider):
    async def complete(self, messages: List[Message]) -> Response:
        # Custom implementation
        return Response(content="...", tokens_used=100)
```

### Memory Plugins

```python
class MemoryPlugin:
    def on_memory_created(self, memory: Memory):
        # Custom processing
        pass
    
    def on_memory_retrieved(self, memories: List[Memory]):
        # Custom filtering
        pass
```

## Development Workflow

### Local Development

```bash
# Start dependencies
docker-compose up -d neo4j

# Run backend with hot reload
uv run uvicorn kairix_apps.server:app --reload

# Run frontend with hot reload
cd kairix-apps/client && npm run dev
```

### Testing Strategy

**Unit Tests**: Component isolation
```python
def test_memory_store():
    store = MemoryStore()
    memory = Memory(content="test")
    id = store.store(memory)
    assert store.retrieve(id).content == "test"
```

**Integration Tests**: End-to-end flows
```python
async def test_chat_completion():
    response = await client.post("/v1/chat/completions", ...)
    assert response.status_code == 200
```

**Load Tests**: Performance validation
```bash
locust -f tests/load/scenarios.py --users 100
```

## Future Architecture

### Planned Enhancements

1. **Multi-Agent Communication**
   - Shared memory protocols
   - Agent message passing
   - Collaborative tasks

2. **Distributed Memory**
   - Sharded storage
   - Federated search
   - Edge caching

3. **Advanced Reasoning**
   - Chain-of-thought
   - Multi-step planning
   - Causal inference

4. **Real-time Learning**
   - Online model updates
   - Preference learning
   - Behavioral adaptation