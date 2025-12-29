## Session 39 - 2025-12-29

### Goals
- [x] Fix podman-compose service startup errors
- [x] Add smart turn detection and OpenTelemetry tracing to voice pipeline
- [x] Deploy Jaeger for trace visualization
- [x] Fix Docker build issues with kairix-common dependency
- [x] Fix worker job failures (LLM_API_KEY, missing prompts)
- [x] Re-add insights cron job with conservative activity check

### What We Covered
- Pipecat interruption detection and VAD configuration
- Smart turn detection with LocalSmartTurnAnalyzerV3
- OpenTelemetry tracing integration with Jaeger
- Docker multi-stage builds with local dependencies
- SAQ worker job configuration and cron scheduling

### Key Concepts Learned
1. **Smart Turn Detection**: LocalSmartTurnAnalyzerV3 uses ML to detect conversation turn boundaries, works with FastAPIWebsocketTransport via `turn_analyzer` param
2. **Pipecat Tracing**: Built-in OpenTelemetry support via `pipecat.utils.tracing.setup` with OTLP exporter
3. **Docker Build Context**: When using local path dependencies (`../kairix-common`), build context must include parent directory
4. **Slim Image Limitations**: Python slim images lack `pgrep`, `ps` - use `/proc/1/cmdline` for healthchecks
5. **SAQ Cron Jobs**: Can run on-demand via `queue.enqueue()` or scheduled via `CronJob` in settings

### What We Built
- **Smart Turn Detection**: Added `LocalSmartTurnAnalyzerV3` to voice pipeline (`server/main.py`)
- **Tracing**: Added Jaeger container + OTLP exporter configuration
- **Docker Fixes**: Updated Dockerfiles to use parent context, copy kairix-common to runtime stage
- **Worker Healthcheck**: Changed from `pgrep` to `cat /proc/1/cmdline | grep saq`
- **CLI Container Safety**: Added default echo commands to prevent accidental service starts
- **Insights Cron**: Re-added with new `INSIGHTS_ACTIVITY_MINUTES` config (default: 1 min)

### Files Modified
- `v2-runtime/src/kairix_agent/server/main.py` - Smart turn + tracing
- `v2-runtime/docker-compose.yml` - Jaeger, build contexts, healthchecks, CLI commands
- `v2-runtime/Dockerfile` - Parent context paths, copy kairix-common to runtime
- `kp3/Dockerfile` - Parent context paths
- `v2-runtime/src/kairix_agent/config.py` - Added INSIGHTS_ACTIVITY_MINUTES
- `v2-runtime/src/kairix_agent/worker/settings.py` - Re-added insights cron job
- `v2-runtime/src/kairix_agent/worker/jobs/insights.py` - Use INSIGHTS_ACTIVITY_MINUTES

### Challenges & Solutions

1. **podman-compose "name in use" errors**
   - Solution: Do `down` before `up` in kx script instead of `--force-recreate`

2. **Docker build: kairix-common not found**
   - Cause: Build context was `.` but pyproject.toml referenced `../kairix-common`
   - Solution: Changed build context to `..`, updated COPY paths in Dockerfile

3. **Runtime: ModuleNotFoundError for kairix_common**
   - Cause: kairix-common only in builder stage, not copied to runtime
   - Solution: Added `COPY --from=builder /kairix-common /kairix-common`

4. **Worker: LLM_API_KEY not found**
   - Cause: Key was in kp3/.env as `KP3_DEEPSEEK_API_KEY`, not in v2-runtime
   - Solution: Added `LLM_API_KEY` to salinas .env

5. **Worker: Missing block_manager_summarizer prompt**
   - Solution: Ran `kp3 world-model seed-prompts` to seed prompts into DB

6. **Worker healthcheck failing**
   - Cause: Slim Python image lacks `pgrep`/`ps`
   - Solution: Use `cat /proc/1/cmdline | tr '\0' ' ' | grep -q saq`

7. **CLI containers running as services**
   - Solution: Added default `command: ["echo", "Usage: ..."]` to exit safely

### Configuration Added
```bash
# Insights job - only trigger if message in last N minutes
INSIGHTS_ACTIVITY_MINUTES=1  # default
```

### Next Steps
- [ ] Test voice pipeline with smart turn detection
- [ ] Analyze traces in Jaeger UI (http://salinas:16686)
- [ ] Monitor insights job triggering during active conversations
- [ ] Investigate Letta ADE memory block display issue

### Notes
- Jaeger ports: 16686 (UI), 4317 (OTLP gRPC), 4318 (OTLP HTTP)
- Insights job runs every minute but skips if no message in last 1 minute
- Voice-admin, sessions-admin, kp3-cli are CLI tools, not persistent services
