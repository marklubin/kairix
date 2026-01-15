# Social Agents User Guide

This guide covers how to set up and use the Kairix Social Agents system for autonomous social media engagement.

## Overview

Social Agents enable your Kairix agents to:
- Monitor social media platforms for mentions, keywords, and interesting content
- Decide whether to engage with posts based on relevance and context
- Draft responses using the agent's personality and knowledge
- Queue drafts for human approval before posting

## Quick Start

### 1. Prerequisites

```bash
# Start infrastructure
./kx dev && ./kx wait all && ./kx migrate

# Generate and export encryption key (one-time setup)
export CREDENTIAL_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Add to your .env file for persistence
echo "CREDENTIAL_ENCRYPTION_KEY=$CREDENTIAL_ENCRYPTION_KEY" >> .env
```

### 2. Create a Social Channel

Connect your agent to a social platform:

```bash
# Via REST API
curl -X POST http://localhost:8000/social/channels \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "your-agent-id",
    "channel_type": "bluesky",
    "handle": "@youragent.bsky.social",
    "credentials": {
      "identifier": "youragent.bsky.social",
      "password": "your-app-password"
    }
  }'
```

### 3. Configure Triggers

Set up when the agent should wake up:

```bash
# Add a keyword trigger
curl -X POST http://localhost:8000/social/channels/{channel_id}/triggers \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_type": "keyword",
    "action": "wake_and_evaluate",
    "config": {"pattern": "AI memory"},
    "cooldown_minutes": 30
  }'
```

### 4. Review Approval Queue

Check pending drafts:

```bash
curl http://localhost:8000/social/approval-queue?agent_id=your-agent-id
```

Approve or reject:

```bash
# Approve
curl -X POST http://localhost:8000/social/approval-queue/{item_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"modified_content": "Optional edited version"}'

# Reject with feedback
curl -X POST http://localhost:8000/social/approval-queue/{item_id}/reject \
  -H "Content-Type: application/json" \
  -d '{"feedback": "Too formal, be more casual"}'
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Social Agent Flow                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    │
│  │   Explore   │───▶│   Evaluate   │───▶│     Draft       │    │
│  │ (cron job)  │    │ (LLM decide) │    │ (LLM generate)  │    │
│  └─────────────┘    └──────────────┘    └─────────────────┘    │
│        │                   │                     │              │
│        ▼                   ▼                     ▼              │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    │
│  │ Interactions│    │   Triggers   │    │ Approval Queue  │    │
│  │   (store)   │    │   (match)    │    │ (human review)  │    │
│  └─────────────┘    └──────────────┘    └─────────────────┘    │
│                                                  │              │
│                                                  ▼              │
│                                          ┌─────────────────┐    │
│                                          │  Post to Social │    │
│                                          │   (if approved) │    │
│                                          └─────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration Options

### Channel Settings

| Field | Type | Description |
|-------|------|-------------|
| `channel_type` | enum | Platform: `bluesky` (more coming) |
| `handle` | string | Social media handle |
| `credentials` | object | Platform-specific auth (encrypted) |
| `engagement_level` | enum | `conservative`, `moderate`, `active` |
| `trust_level` | enum | `learning`, `supervised`, `autonomous` |
| `enabled` | bool | Enable/disable channel |

### Engagement Levels

- **Conservative**: Only respond to direct mentions
- **Moderate**: Engage with relevant conversations
- **Active**: Proactively participate in discussions

### Trust Levels

- **Learning**: All drafts require approval (recommended for new agents)
- **Supervised**: High-confidence responses auto-post, others need approval
- **Autonomous**: Agent posts directly (use with caution)

### Trigger Types

| Type | Config | Description |
|------|--------|-------------|
| `direct_mention` | `{}` | Someone @mentions the agent |
| `reply_to_post` | `{}` | Someone replies to agent's post |
| `keyword` | `{"pattern": "..."}` | Content matches keyword/phrase |
| `account_post` | `{"watched_handles": [...]}` | Specific accounts post |
| `engagement_threshold` | `{"min_likes": N}` | High-engagement posts |

### Trigger Actions

- **wake_and_evaluate**: Full evaluation and potential response
- **surface_to_user**: Notify user but don't auto-respond
- **log_only**: Just record the interaction

## API Reference

### Channels

```
GET    /social/channels                    # List all channels
GET    /social/channels?agent_id=X         # List channels for agent
POST   /social/channels                    # Create channel
GET    /social/channels/{id}               # Get channel details
PATCH  /social/channels/{id}               # Update channel
DELETE /social/channels/{id}               # Delete channel
```

### Triggers

```
GET    /social/channels/{id}/triggers      # List triggers
POST   /social/channels/{id}/triggers      # Create trigger
PATCH  /social/triggers/{id}               # Update trigger
DELETE /social/triggers/{id}               # Delete trigger
```

### Interactions

```
GET    /social/channels/{id}/interactions  # List interactions
GET    /social/interactions/{id}           # Get interaction details
```

### Approval Queue

```
GET    /social/approval-queue              # List pending items
GET    /social/approval-queue/{id}         # Get item details
POST   /social/approval-queue/{id}/approve # Approve draft
POST   /social/approval-queue/{id}/reject  # Reject draft
GET    /social/approval-queue/stats        # Queue statistics
```

## Background Jobs

The social system uses three SAQ background jobs:

### social_explore

Runs on schedule (configurable cron) to:
- Fetch timeline posts
- Fetch mentions since last check
- Store interactions in database
- Evaluate triggers and enqueue follow-up jobs

### social_evaluate

Called when a trigger fires:
- Builds context from the interaction
- Uses BlockManagerAgent to decide engagement
- Enqueues draft job if agent should respond

### social_draft

Called after positive evaluation:
- Gathers full context (interaction, thread, user profile)
- Uses BlockManagerAgent to generate response
- Creates approval queue item (or auto-posts if trust allows)

## Testing

### Unit Tests (No Infrastructure)

```bash
uv run pytest tests/social/ --ignore=tests/social/e2e/ -v
# 58 tests, ~1-2 seconds
```

### Integration Tests (PostgreSQL Required)

```bash
./kx dev && ./kx wait postgres && ./kx migrate
uv run pytest tests/social/e2e/ -v -m integration
# 17 tests
```

### Full Functional Tests (All Services)

```bash
./kx dev && ./kx wait all && ./kx migrate
uv run pytest tests/social/e2e/test_full_social_flow.py -v -m integration
# 6 tests with real Letta agent provisioning
```

## Security Considerations

### Credential Encryption

All platform credentials are encrypted using Fernet symmetric encryption before storage:

```python
# Credentials are never stored in plaintext
channel.credentials_encrypted = encrypt_credentials({
    "identifier": "...",
    "password": "..."
})
```

### Environment Variables

Required:
- `CREDENTIAL_ENCRYPTION_KEY`: Fernet key for credential encryption

Keep this key secure - losing it means losing access to stored credentials.

### Rate Limiting

The system includes cooldown periods on triggers to prevent:
- Spam responses
- API rate limit violations
- Excessive engagement

Default cooldown: 30 minutes per trigger.

## Troubleshooting

### Channel Auth Failures

```bash
# Check channel status
curl http://localhost:8000/social/channels/{id}

# Verify credentials by re-creating channel
curl -X DELETE http://localhost:8000/social/channels/{id}
# Then create new channel with fresh credentials
```

### Triggers Not Firing

1. Check trigger is enabled: `"enabled": true`
2. Check cooldown hasn't blocked: `last_fired_at` vs `cooldown_minutes`
3. Verify pattern matching (keywords are case-insensitive)

### Drafts Not Appearing

1. Check agent's Letta ID is correct
2. Verify BlockManagerAgent can reach Letta server
3. Check evaluation job completed (look in SAQ logs)

## Roadmap

- [ ] Twitter/X platform support
- [ ] Mastodon platform support
- [ ] OAuth flow for easier credential setup
- [ ] Web UI for approval queue
- [ ] Analytics dashboard
- [ ] Multi-language support
- [ ] Thread-aware conversations
