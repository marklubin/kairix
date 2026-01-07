## Session 45 - 2026-01-06

### Goals
- [x] Containerize vLLM inference in docker-compose
- [x] Add Kokoro TTS to docker-compose for consistent deployment
- [x] Test voice pipeline end-to-end through agent server
- [x] Investigate and document voice response latency

### What We Covered
- vLLM containerization with GPU passthrough
- Kokoro TTS integration replacing Cartesia for local inference
- Silero VAD tuning for speech detection sensitivity
- vLLM prefix caching behavior and first-request latency

### Key Concepts Learned
1. **vLLM Prefix Caching**: First request processes full context (~3000+ tokens) from scratch. Subsequent requests reuse cached prefix, significantly reducing latency.
2. **VAD Tuning Trade-offs**: `start_secs` controls speech detection speed (lower = faster but more false positives), `stop_secs` controls end-of-speech delay (lower = snappier but may cut off mid-sentence).
3. **Letta vLLM Integration**: Letta uses `VLLM_API_BASE` env var to connect to OpenAI-compatible endpoints. Model format: `openai/<model>` for vLLM backend.
4. **TTS Provider Selection**: Currently hardcoded via `TTS_PROVIDER` env var. Plan notes bug: should use `db_voice.provider` from voices table instead.

### What We Built
- Added vLLM service to docker-compose (GPU 0, port 8001)
- Added Kokoro TTS service to docker-compose (GPU 1, port 8880)
- Updated Letta service with vLLM connection
- Updated kairix-server with Kokoro TTS configuration
- Tuned VAD parameters for better speech detection

### Files Modified
- `v2-runtime/docker-compose.yml` - Added vLLM and Kokoro services, updated Letta and kairix-server
- `v2-runtime/src/kairix_agent/server/main.py` - VAD params: start_secs 0.1, stop_secs 0.2, min_volume 0.4
- `v2-runtime/.env` - Added VLLM_MODEL, VLLM_MAX_MODEL_LEN, HF_CACHE_DIR

### Challenges & Solutions
- **Challenge**: Voice pipeline not detecting speech ("IDLE: Unexpected TranscriptionFrame")
  - **Solution**: Lowered VAD start_secs from 0.2 to 0.1, min_volume from 0.6 to 0.4

- **Challenge**: ~5 second latency from user message to TTS response
  - **Root Cause**: Large prompt prefill (~3000+ tokens for system prompt + all memory blocks) with no prefix cache hit on first request
  - **Solution**: Documented behavior; subsequent requests benefit from prefix caching

- **Challenge**: Container dependencies blocking restarts
  - **Solution**: Force removed exited dependent containers before recreating

### Insights & Aha Moments
- The Letta system prompt + memory blocks totals ~3000+ tokens - this is significant prefill overhead
- Prefix caching is essential for voice latency; first request will always be slower
- VAD parameters are environment-sensitive; what works in one room may need tuning in another

### Architecture Notes

**GPU Allocation (salinas):**
- GPU 0 (RTX 3060 12GB): vLLM inference
- GPU 1 (RTX 3050 6GB): Kokoro TTS + KP3 embeddings

**Voice Pipeline Flow:**
```
Audio → FastAPIWebsocketTransport → SileroVAD → DeepgramSTT → UserTurnAggregator → LettaLLM → KokoroTTS → Audio
```

**Latency Breakdown (first request):**
- Speech detection: ~100-200ms (VAD)
- Transcription: ~500ms (Deepgram)
- LLM inference: ~4-5s (vLLM, cold prefix)
- TTS synthesis: ~200ms (Kokoro)

### Plan Created
Created comprehensive plan for Unified Agent Configuration Model at:
`~/.claude/plans/foamy-fluttering-lobster.md`

Key points:
- Single `agents` table as source of truth
- Per-agent LLM config (inference_model, inference_provider_url)
- All blocks use KP3 refs for content management
- BlockManagerAgent writes to KP3 refs, hooks sync to Letta
- Bug fix: TTS provider should come from voices table, not env var

### Next Steps
- [ ] Test second voice request to verify prefix caching reduces latency
- [ ] Begin Phase 1 of Unified Agent Configuration plan (database & models)
- [ ] Fix TTS provider selection to use db_voice.provider

### Commands Reference
```bash
# Check vLLM status
ssh salinas 'podman logs --tail 20 vllm'

# Check prefix cache metrics
ssh salinas 'curl -s http://localhost:8001/metrics | grep cache'

# Deploy changes
./kx deploy salinas

# Test voice endpoint
# Connect via KMP app to /voice?agent_id=<agent_id>
```
