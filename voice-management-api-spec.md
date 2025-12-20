# Voice Management API Specification

## Base URL
`/voices`

---

## Types

```typescript
// Voice entity
interface Voice {
  id: string;                    // UUID
  name: string;                  // e.g., "Friendly Female"
  provider_voice_id: string;     // Cartesia voice ID
  provider: "cartesia";          // Only cartesia for now
  description: string | null;
  created_at: string;            // ISO 8601 timestamp
  updated_at: string | null;     // ISO 8601 timestamp
}

// Agent voice settings response
interface AgentVoiceSettings {
  agent_id: string;              // Letta agent ID
  voice: Voice | null;           // null if no voice configured
}

// Request bodies
interface CreateVoiceRequest {
  name: string;
  provider_voice_id: string;
  provider?: string;             // defaults to "cartesia"
  description?: string | null;
}

interface UpdateVoiceRequest {
  name?: string;
  provider_voice_id?: string;
  description?: string | null;
}

interface SetAgentVoiceRequest {
  voice_id: string;              // UUID of voice from voices table
}

// Response for setting agent voice
interface SetAgentVoiceResponse {
  agent_id: string;
  voice_id: string;
  active_pipelines_updated: number;  // how many live sessions were updated
}
```

---

## Endpoints

### List Voices
```
GET /voices
```
**Response**: `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Friendly Female",
    "provider_voice_id": "a0e99841-438c-4a64-b679-ae501e7d6091",
    "provider": "cartesia",
    "description": "Warm and approachable voice",
    "created_at": "2025-12-19T10:00:00Z",
    "updated_at": null
  }
]
```

---

### Get Voice
```
GET /voices/{voice_id}
```
**Response**: `200 OK` - Voice object
**Error**: `404 Not Found` - `{"detail": "Voice not found"}`

---

### Create Voice
```
POST /voices
Content-Type: application/json

{
  "name": "Calm Male",
  "provider_voice_id": "79a125e8-cd45-4c13-8a67-188112f4dd22",
  "provider": "cartesia",
  "description": "Soothing and professional"
}
```
**Response**: `201 Created` - Voice object

---

### Update Voice
```
PATCH /voices/{voice_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "description": "New description"
}
```
**Response**: `200 OK` - Voice object
**Error**: `404 Not Found`

---

### Delete Voice
```
DELETE /voices/{voice_id}
```
**Response**: `204 No Content`
**Error**: `404 Not Found`

---

### Get Agent's Voice
```
GET /voices/agents/{agent_id}
```
**Response**: `200 OK`
```json
{
  "agent_id": "agent-abc123",
  "voice": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Friendly Female",
    "provider_voice_id": "a0e99841-438c-4a64-b679-ae501e7d6091",
    "provider": "cartesia",
    "description": "Warm and approachable",
    "created_at": "2025-12-19T10:00:00Z",
    "updated_at": null
  }
}
```
Or if no voice configured:
```json
{
  "agent_id": "agent-abc123",
  "voice": null
}
```

---

### Set Agent's Voice
```
PUT /voices/agents/{agent_id}
Content-Type: application/json

{
  "voice_id": "550e8400-e29b-41d4-a716-446655440000"
}
```
**Response**: `200 OK`
```json
{
  "agent_id": "agent-abc123",
  "voice_id": "550e8400-e29b-41d4-a716-446655440000",
  "active_pipelines_updated": 1
}
```
**Error**: `404 Not Found` - `{"detail": "Voice not found"}`

---

## Notes

- `active_pipelines_updated` tells you how many live voice WebSocket sessions had their voice changed in real-time
- If the agent has no active voice session, the change is still persisted and will apply on next connection
- The `/voice` WebSocket endpoint will accept an optional `?agent_id=xxx` query param to look up the voice
