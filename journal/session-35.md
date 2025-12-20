## Session 35 - Date: 2025-12-19

### Goals
- [x] Add voices to the database via CLI
- [x] Debug real-time voice pipeline updates not working
- [x] Document deployment and kx CLI in CLAUDE.md

### What We Covered
- Voice management REST API usage for adding/assigning voices
- Debugging VoicePipelineManager singleton issues across uvicorn workers
- Understanding uvicorn multi-worker process isolation

### Key Concepts Learned
1. **Uvicorn Workers and Process Isolation**: Each uvicorn worker runs in its own process with its own memory space. Singleton patterns (like `voice_pipeline_manager`) don't share state across workers. WebSocket connections handled by worker A can't be updated by REST requests handled by worker B.

2. **TTSUpdateSettingsFrame**: Pipecat's mechanism for dynamically changing TTS settings mid-conversation. Queue the frame directly to the CartesiaTTSService instance with `settings={"voice_id": "..."}` format.

### What We Built
- Added voices via REST API: "mark" and "cindy" Cartesia voices
- Assigned voice to agent via PUT endpoint
- Added "v2-runtime Operations" section to `/Users/mark/kairix/CLAUDE.md`:
  - kx CLI command reference
  - deploy.sh usage documentation
  - Remote command execution examples

### Insights & Aha Moments
- **Root cause of voice update failure**: The server was running with `--workers 2`, so the VoicePipelineManager singleton existed separately in each worker. When a voice WebSocket connected to worker 1 and a PUT request went to worker 2, worker 2's pipeline manager had no registered pipelines.
- The logs clearly showed it: registration happened at 05:15:41 in one process, but "No active pipelines" at 05:15:51 because the PUT hit a different process.

### Challenges & Solutions
- **Challenge**: Voice updates via PUT weren't reaching active voice sessions
- **Investigation**: Checked logs, found "No active pipelines" despite active WebSocket
- **Root Cause**: `--workers 2` in docker-compose.yml meant separate process memory
- **Solution**: Changed to `--workers 1` for now. Future: Redis-based pipeline tracking for horizontal scaling.

### Code Changes
- `docker-compose.yml`: Changed `--workers 2` to `--workers 1` for kairix-server
- `pipeline_manager.py`: Changed "No active pipelines" log from DEBUG to INFO
- `router.py`: Added logging when PUT /voices/agents/{id} is called
- `CLAUDE.md`: Added v2-runtime Operations section with kx CLI and deploy.sh docs

### Next Steps
- [ ] Test real-time voice switching with single worker
- [ ] Consider Redis-based VoicePipelineManager for multi-worker support
- [ ] Build voice management UI in the app

### Questions/Blockers
- For horizontal scaling, will need to implement Redis pub/sub for pipeline updates across workers
