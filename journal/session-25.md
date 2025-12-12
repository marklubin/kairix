## Session 25 - [Date: 2025-12-08]

### Goals
- [x] Manual deployment to salinas server
- [x] Transplant Corindel agent using Letta .af file export/import
- [x] Full agent provisioning and verification
- [x] End-to-end iOS app test

### What We Covered
- Letta Agent File (.af) format for agent export/import
- Manual server deployment workflow with podman-compose
- Environment variable refactoring for deployment flexibility
- Podman networking and compose file configuration
- iOS app endpoint configuration

### Key Concepts Learned

1. **Letta Agent File (.af) Format**: Open standard for serializing stateful AI agents. Includes agent config, memory blocks, and archival memory (conversation history). Export via Letta Desktop UI or API (`/v1/agents/{id}/export`), import via POST to `/v1/agents/import`.

2. **Podman Registry Configuration**: Podman requires fully-qualified image names by default. Fix by adding `unqualified-search-registries = ["docker.io"]` to `/etc/containers/registries.conf`.

3. **Compose Network Inheritance**: When using multiple compose files (`-f base.yml -f override.yml`), don't declare networks as `external: true` in override files - they can't merge dict with NoneType. Just omit the networks section entirely to inherit from base.

4. **Environment Variable Quoting**: Env vars with quotes in `.env` files (e.g., `VAR="value"`) pass the quotes as part of the value, causing validation errors like `"agent-id"` instead of `agent-id`.

5. **LaunchedEffect Recomposition**: In Compose, `LaunchedEffect(key)` re-triggers whenever the key changes - useful for reconnecting to different endpoints when selection changes.

### What We Built

**Server Deployment Changes:**
- `src/kairix_agent/config.py` - Added `MONITORED_AGENT_IDS` env var
- `src/kairix_agent/worker/settings.py` - Build `MONITORED_AGENTS` from env vars instead of hardcoding
- `src/kairix_agent/memory/letta_memory.py` - Use `Config.LETTA_BASE_URL` as default
- `src/kairix_agent/server/provider/letta.py` - Use `Config.LETTA_BASE_URL` as default
- `src/kairix_agent/server/pipecat/letta_llm.py` - Use `Config.LETTA_BASE_URL` as default
- `src/kairix_agent/scripts/test_jobs.py` - Use `Config.LETTA_BASE_URL` as default
- `docker-compose.dev.yml` / `docker-compose.prod.yml` - Removed external network declarations

**iOS App Changes:**
- `App.kt` - Updated Salinas agent ID, added top padding for camera cutout

### Insights & Aha Moments

- **Agent transplant workflow**: Export .af from source Letta, import to target Letta, then run provisioning for subsidiary agents (reflector, insights) which attach to the imported conversational agent's shared blocks.

- **The .af import creates a NEW agent ID** - must update all references (.env, worker settings, iOS app endpoints) after import.

- **Podman-compose quirks**: No `--force-recreate` equivalent that works smoothly. Workflow is `podman rm -f <container>` then `up -d`.

### Challenges & Solutions

- **Challenge**: Podman couldn't pull images - "short-name did not resolve"
- **Solution**: Added `unqualified-search-registries = ["docker.io"]` to `/etc/containers/registries.conf`

- **Challenge**: Compose network merge error - "can't merge dict and NoneType"
- **Solution**: Removed networks section entirely from override compose files

- **Challenge**: Agent ID validation error with extra quotes
- **Solution**: Removed quotes from `.env` file values

- **Challenge**: Terminal type not recognized on salinas (kitty)
- **Solution**: Added `SetEnv TERM=xterm-256color` to SSH config

### Deployment Checklist (for future reference)

1. Export agent from source Letta Desktop (`.af` file)
2. SSH to target, pull latest code
3. Start infrastructure: `podman-compose -f docker-compose.yml up -d`
4. Copy and import `.af` file, note new agent ID
5. Update `.env` with new `LETTA_AGENT_ID` and `MONITORED_AGENT_IDS`
6. Build and run provisioning in temp container for subsidiary agents
7. Run Alembic migrations
8. Build and start app services: `podman-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
9. Verify via health check, Dozzle logs, iOS app test

### Next Steps
- [ ] Consider adding deployment script improvements for smoother container recreation
- [ ] Document agent transplant workflow in CLAUDE.md or README
- [ ] Explore Letta's agent versioning/checkpointing for rollback capability

### Questions/Blockers
- None - deployment successful!
