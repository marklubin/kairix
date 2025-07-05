# Kairix API Reference

Kairix provides a comprehensive API for building memory-enabled AI applications. This reference covers the REST API, Python SDK, and data models.

## Table of Contents

1. [REST API](#rest-api)
2. [Python SDK](#python-sdk)
3. [Data Models](#data-models)
4. [WebSocket API](#websocket-api)
5. [Authentication](#authentication)
6. [Error Handling](#error-handling)

## REST API

Base URL: `http://localhost:8080/v1`

### Chat Completions

**POST** `/v1/chat/completions`

OpenAI-compatible chat completions with memory context.

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "kairix-gpt-4",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "agent_id": "my-agent",
    "stream": false
  }'
```

**Request Body:**
```json
{
  "model": "string",           // Model ID (required)
  "messages": [                // Message history (required)
    {
      "role": "string",        // "user", "assistant", "system"
      "content": "string"      // Message content
    }
  ],
  "agent_id": "string",        // Agent identifier (required)
  "stream": false,             // Stream response (optional)
  "temperature": 0.7,          // Sampling temperature (optional)
  "max_tokens": 1000,          // Max response length (optional)
  "memory_depth": 10,          // How many memories to retrieve (optional)
  "include_reflections": true  // Include agent reflections (optional)
}
```

**Response:**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677858242,
  "model": "kairix-gpt-4",
  "usage": {
    "prompt_tokens": 13,
    "completion_tokens": 7,
    "total_tokens": 20
  },
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "I'm doing well, thank you!"
      },
      "finish_reason": "stop",
      "index": 0
    }
  ],
  "memory_context": {
    "memories_used": 5,
    "relevance_scores": [0.92, 0.87, 0.85, 0.81, 0.79]
  }
}
```

### Models

**GET** `/v1/models`

List available models.

```bash
curl http://localhost:8080/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "kairix-gpt-4",
      "object": "model",
      "created": 1677858242,
      "owned_by": "kairix",
      "permission": [],
      "root": "gpt-4",
      "parent": null
    },
    {
      "id": "kairix-llama2-70b",
      "object": "model",
      "created": 1677858242,
      "owned_by": "kairix",
      "permission": [],
      "root": "llama2",
      "parent": null
    }
  ]
}
```

### Agents

**POST** `/v1/agents`

Create a new agent.

```bash
curl -X POST http://localhost:8080/v1/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "name": "Research Assistant",
    "persona_type": "analytical",
    "model": "kairix-gpt-4"
  }'
```

**GET** `/v1/agents/{agent_id}`

Get agent details.

**PUT** `/v1/agents/{agent_id}`

Update agent configuration.

**DELETE** `/v1/agents/{agent_id}`

Delete an agent and all associated memories.

### Memory Operations

**GET** `/v1/agents/{agent_id}/memories`

List agent memories.

```bash
curl http://localhost:8080/v1/agents/{agent_id}/memories \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Query Parameters:**
- `type`: Filter by memory type (experiential, conceptual, reflective)
- `limit`: Number of memories to return (default: 50)
- `offset`: Pagination offset
- `search`: Search memories by content
- `start_date`: Filter by date range
- `end_date`: Filter by date range

**POST** `/v1/agents/{agent_id}/memories`

Create a memory directly.

```bash
curl -X POST http://localhost:8080/v1/agents/{agent_id}/memories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "type": "conceptual",
    "content": "User prefers morning meetings",
    "importance": 0.8,
    "metadata": {
      "source": "explicit_feedback",
      "confidence": 0.95
    }
  }'
```

**DELETE** `/v1/agents/{agent_id}/memories/{memory_id}`

Delete a specific memory.

### Context Updates

**POST** `/v1/context/update`

Update agent context with external information.

```bash
curl -X POST http://localhost:8080/v1/context/update \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "agent_id": "my-agent",
    "updates": {
      "current_time": "2024-01-15T10:30:00Z",
      "location": "San Francisco, CA",
      "weather": "Sunny, 72°F",
      "calendar_next": "Team standup in 30 minutes"
    }
  }'
```

## Python SDK

### Installation

```bash
pip install kairix
# or with uv
uv add kairix
```

### Quick Start

```python
from kairix import KairixClient, Agent, Memory
from kairix.types import PersonaType, MemoryType

# Initialize client
client = KairixClient(
    base_url="http://localhost:8080",
    api_key="your_api_key"
)

# Create an agent
agent = client.create_agent(
    name="Assistant",
    persona_type=PersonaType.CONVERSATIONAL,
    model="kairix-gpt-4"
)

# Chat with the agent
response = agent.chat("Hello! Tell me about yourself.")
print(response.content)

# Access memories
memories = agent.get_memories(
    memory_type=MemoryType.EXPERIENTIAL,
    limit=10
)

for memory in memories:
    print(f"{memory.timestamp}: {memory.content}")
```

### Advanced Usage

```python
# Streaming responses
for chunk in agent.chat_stream("Tell me a story"):
    print(chunk.content, end="")

# Batch memory operations
memories = [
    Memory(
        type=MemoryType.CONCEPTUAL,
        content="User is a software engineer",
        importance=0.9
    ),
    Memory(
        type=MemoryType.EXPERIENTIAL,
        content="Discussed Python best practices",
        importance=0.7
    )
]
agent.add_memories(memories)

# Search memories semantically
results = agent.search_memories(
    query="programming languages",
    limit=5
)

# Trigger reflection
reflection = agent.reflect(
    prompt="What have you learned about the user's work style?"
)
```

### Async Support

```python
import asyncio
from kairix import AsyncKairixClient

async def main():
    client = AsyncKairixClient(
        base_url="http://localhost:8080",
        api_key="your_api_key"
    )
    
    agent = await client.create_agent(
        name="Async Assistant",
        persona_type=PersonaType.TASK_FOCUSED
    )
    
    # Concurrent operations
    tasks = [
        agent.chat("What's the weather?"),
        agent.chat("What's on my calendar?"),
        agent.get_memories(limit=5)
    ]
    
    results = await asyncio.gather(*tasks)

asyncio.run(main())
```

## Data Models

### Agent

```python
class Agent:
    id: str
    name: str
    persona_type: PersonaType
    model: str
    created_at: datetime
    updated_at: datetime
    config: AgentConfig
    memory_stats: MemoryStats
```

### Memory

```python
class Memory:
    id: str
    agent_id: str
    type: MemoryType
    content: str
    embedding: Optional[List[float]]
    importance: float
    timestamp: datetime
    metadata: Dict[str, Any]
    source: MemorySource
    related_memories: List[str]
```

### MemoryType

```python
class MemoryType(Enum):
    EXPERIENTIAL = "experiential"   # Direct experiences
    CONCEPTUAL = "conceptual"       # Learned concepts
    REFERENCE = "reference"         # Static information
    REFLECTIVE = "reflective"       # Self-generated insights
    TASK_STATE = "task_state"       # Ongoing task context
```

### PersonaType

```python
class PersonaType(Enum):
    CONVERSATIONAL = "conversational"
    TASK_FOCUSED = "task_focused"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    CUSTOM = "custom"
```

## WebSocket API

For real-time streaming and bidirectional communication.

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8080/v1/chat/stream');

ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'auth',
        api_key: 'your_api_key'
    }));
};
```

### Streaming Chat

```javascript
// Send message
ws.send(JSON.stringify({
    type: 'chat',
    agent_id: 'my-agent',
    message: 'Hello!',
    include_memory_context: true
}));

// Receive streaming response
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'content':
            console.log(data.content);
            break;
        case 'memory_context':
            console.log('Memories used:', data.memories);
            break;
        case 'done':
            console.log('Response complete');
            break;
        case 'error':
            console.error('Error:', data.error);
            break;
    }
};
```

## Authentication

### API Key Authentication

Include your API key in the Authorization header:

```
Authorization: Bearer YOUR_API_KEY
```

### OAuth 2.0 (Coming Soon)

OAuth 2.0 support for third-party integrations.

## Error Handling

### Error Response Format

```json
{
  "error": {
    "message": "Invalid agent_id provided",
    "type": "invalid_request_error",
    "param": "agent_id",
    "code": "invalid_agent"
  }
}
```

### Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid API key |
| 403 | Forbidden - Access denied |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Rate Limiting

Default limits:
- 60 requests per minute per API key
- 1000 requests per hour per API key
- 10 concurrent connections per API key

Headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1677858242
```

## Code Examples

### Process ChatGPT Export

```python
from kairix import KairixClient
from kairix.importers import ChatGPTImporter

client = KairixClient(api_key="your_api_key")
importer = ChatGPTImporter(client)

# Import conversations
result = importer.import_file(
    "export.json",
    agent_id="my-agent",
    process_memories=True
)

print(f"Imported {result.conversation_count} conversations")
print(f"Created {result.memory_count} memories")
```

### Custom Perceptor

```python
from kairix.perceptors import BasePerceptor
from kairix.types import PerceptionData

class WeatherPerceptor(BasePerceptor):
    async def perceive(self, context):
        weather_data = await self.fetch_weather(context.location)
        return PerceptionData(
            type="environmental",
            content=f"Current weather: {weather_data}",
            importance=0.3
        )

# Register custom perceptor
agent.register_perceptor(WeatherPerceptor())
```

### Memory Export

```python
# Export all memories
memories = agent.export_memories(format="json")
with open("agent_backup.json", "w") as f:
    json.dump(memories, f)

# Export specific date range
memories = agent.export_memories(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31),
    format="csv"
)
```

## Best Practices

1. **Use Appropriate Memory Types**: Choose the right type for each memory
2. **Set Importance Scores**: Help agents prioritize memories
3. **Batch Operations**: Use bulk endpoints for better performance
4. **Handle Errors Gracefully**: Implement retry logic for transient failures
5. **Monitor Rate Limits**: Track usage to avoid hitting limits
6. **Secure API Keys**: Never expose keys in client-side code
7. **Use Streaming for Long Responses**: Better UX for lengthy outputs
8. **Implement Webhooks**: For async operations and notifications