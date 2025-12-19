## Session 31 - 2025-12-18

### Goals
- [x] Verify KP3 embedding backfill on salinas
- [x] Enable Ollama as provider in Letta
- [x] Configure Ollama performance env vars
- [x] Fix container networking issues

### What We Covered
- KP3 database verification on salinas
- Letta + Ollama integration
- Podman container networking troubleshooting
- Ollama systemd configuration

### Key Concepts Learned

1. **Letta Ollama Integration**: To enable Ollama as a model provider in Letta, set `OLLAMA_BASE_URL=http://host.containers.internal:11434` in the .env file. Models are then available with handles like `ollama/model-name`.

2. **Podman Network Issues**: When containers get recreated individually, they can end up on different networks (e.g., `v2-runtime_kairix-net` vs `agent-server_kairix-net`). Fix by doing a full `podman-compose down && up` to ensure all containers are on the same network.

3. **Ollama Performance Tuning**: Key env vars for systemd override:
   - `OLLAMA_FLASH_ATTENTION=1` - Free perf improvement
   - `OLLAMA_KV_CACHE_TYPE=q8_0` - Cuts cache memory in half
   - `OLLAMA_KEEP_ALIVE=60m` - Keep models loaded longer
   - `OLLAMA_CONTEXT_LENGTH=32000` - Default context window

4. **podman-compose Quirks**: `restart` doesn't reload env_file changes - must `down` and `up` to pick up new environment variables.

### What We Built

**Ollama Setup Script** (`~/setup-ollama-env.sh` on salinas):
- Creates systemd override for Ollama service
- Adds performance tuning env vars
- Restarts and verifies the service

**Letta Configuration**:
- Added `OLLAMA_BASE_URL` to v2-runtime/.env
- Verified `ollama/gpt-oss:20b` and `ollama/qwen3-embedding:4b` available

### Verification Results

**KP3 on Salinas:**
| Metric | Value |
|--------|-------|
| Total passages | 3,880 |
| With embeddings | 3,880 (100%) |
| Source | kairix_backup |
| Search modes | FTS, semantic, hybrid all working |

**Container Status (after fixes):**
- kairix-postgres: healthy
- kairix-redis: healthy
- kairix-server: healthy
- kairix-worker: healthy
- letta: running

### Challenges & Solutions

- **Challenge**: Letta giving OpenAI auth error despite switching to Ollama model
- **Solution**: Agent model handle needed `ollama/` prefix (e.g., `ollama/gpt-oss:20b`)

- **Challenge**: kairix-worker couldn't resolve kairix-redis DNS
- **Solution**: Containers were on different networks from partial restarts. Full `down && up` fixed it.

- **Challenge**: SSH sudo commands timeout (need interactive password)
- **Solution**: Created shell script on salinas for user to run manually

### Next Steps
- [ ] Run Ollama setup script on salinas (requires sudo)
- [ ] Test agent with Ollama model end-to-end
- [ ] Consider adding more Ollama chat models

### Questions/Blockers
- Anthropic credits low (separate issue from Ollama work)
