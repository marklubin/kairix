---

## Session 47 - 2026-01-19

### Goals
- [x] Implement LiteLLM proxy integration for unified LLM observability
- [x] Add self-hosted Langfuse for LLM tracing
- [x] Route all LLM calls (OpenAI, vLLM, DeepSeek) through LiteLLM
- [x] Deploy to salinas and verify services

### What We Covered
- LiteLLM proxy setup for unified LLM routing and observability
- Langfuse v2 self-hosted deployment (v3 requires ClickHouse, v2 uses PostgreSQL)
- Docker compose service orchestration with proper dependency chains
- Podman container dependency graph debugging

### Key Concepts Learned
1. **Langfuse v2 vs v3**: Langfuse v3 requires ClickHouse in addition to PostgreSQL. For simpler self-hosting, v2 works with PostgreSQL alone.
2. **LiteLLM Proxy**: Routes multiple LLM backends through a single endpoint, adding unified observability via callbacks to Langfuse and OTLP.
3. **Podman Dependency Graphs**: When containers have `depends_on` chains, removing intermediate containers can break the dependency graph. Clean restart required.

### What We Built

#### New Files Created
- `v2-runtime/litellm_config.yaml` - LiteLLM routing configuration for 6 models
- `v2-runtime/.env.example` - Environment variable template with Langfuse vars

#### Files Modified
- `v2-runtime/docker-compose.yml`:
  - Added `langfuse` service (port 3000) using `langfuse/langfuse:2`
  - Added `litellm` service (port 4000) with model routing
  - Updated `letta` to route through LiteLLM (`VLLM_API_BASE`, `OPENAI_API_BASE`)
  - Updated `kairix-worker` with `LLM_BASE_URL=http://litellm:4000/v1`

### Architecture Implemented

```
                              ┌─────────────┐
                              │             │ ──→ OpenAI API (gpt-5.2, 4o, 4o-mini)
Letta ──────────────────────→ │   LiteLLM   │ ──→ vLLM (local Qwen)
                              │   :4000     │
BlockManagerAgent ──────────→ │             │ ──→ DeepSeek API
                              └──────┬──────┘
                                     │
                         ┌───────────┴───────────┐
                         ▼                       ▼
                    Langfuse              OpenObserve
                    :3000                 :5081 (OTLP)
```

### Current Service Status on Salinas

| Service | Status | Port | Notes |
|---------|--------|------|-------|
| Langfuse | Healthy | 3000 | v2.95.11, needs API keys configured |
| LiteLLM | Healthy | 4000 | 6 models routed |
| kairix-server | Healthy | 8000 | |
| kairix-worker | Healthy | - | |
| vLLM | Running | 8001 | Qwen2.5-7B-AWQ |
| Letta | Running | 9000 | Routing through LiteLLM |

### Git Commits Made
1. `d475945` - feat: Add LiteLLM proxy for unified LLM observability
2. `ed4aa05` - fix: Use Langfuse v2 image (PostgreSQL-only, no ClickHouse)

### Next Steps
- [ ] Open http://salinas:3000 and create Langfuse admin account
- [ ] Generate API keys in Langfuse (Settings → API Keys)
- [ ] Add `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` to `.env` on salinas
- [ ] Restart litellm: `./kx restart litellm`
- [ ] Send test message through voice/text pipeline
- [ ] Verify traces appear in Langfuse dashboard (prompts, completions, latency, tokens)
- [ ] Check OpenObserve for OTLP spans

### Quick Resume Commands
```bash
# SSH to salinas and check status
ssh salinas 'cd ~/kairix/v2-runtime && ./kx status'

# View Langfuse logs
ssh salinas 'podman logs langfuse'

# View LiteLLM logs
ssh salinas 'podman logs litellm'

# Restart litellm after adding API keys
ssh salinas 'cd ~/kairix/v2-runtime && ./kx restart litellm'

# Test LiteLLM health
ssh salinas 'curl -s http://localhost:4000/health | jq .healthy_count'
```

### URLs
- **Langfuse UI**: http://salinas:3000
- **LiteLLM Health**: http://salinas:4000/health
- **OpenObserve**: http://salinas:5080 (admin@kairix.local / kairix123)
- **Kairix API**: http://salinas:8000

### Notes
- Langfuse database was created: `CREATE DATABASE langfuse;`
- LiteLLM callbacks configured for both `langfuse` and `otel` in `litellm_config.yaml`
- All services deployed via `./kx dev` (infrastructure) - app profile services start automatically due to dependencies
