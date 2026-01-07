## Session 44 - 2026-01-06

### Goals
- [x] Refactor KP3 embedding generation from Ollama to vLLM in-process
- [x] Fix GPU memory allocation (use smaller model, correct GPU assignment)
- [x] Fix `kx kp3 passage search` CLI command
- [x] Add `--agent-name` option for case-insensitive agent lookup

### What We Covered
- vLLM embedding API migration and configuration
- GPU memory management across multiple GPUs
- Podman container GPU passthrough via CDI
- CLI refactoring to use HTTP API instead of loading models directly

### Key Concepts Learned
1. **vLLM Embedding API**: Use `LLM(model=..., task="embed")` in vLLM 0.8.x (not `runner="pooling"`)
2. **MRL (Matryoshka Representation Learning)**: Truncating embeddings from 2560 to 1024 dims for efficiency
3. **CDI (Container Device Interface)**: Podman's GPU passthrough method using `devices: nvidia.com/gpu=all`
4. **GPU Isolation**: Use `CUDA_VISIBLE_DEVICES=1` to restrict container to specific GPU

### What We Built
- Migrated embedding generation from Ollama to vLLM in-process
- Configured GPU 1 (RTX 3050 6GB) for embeddings, GPU 0 (RTX 3060 12GB) reserved for inference
- Fixed `kx kp3` command to use podman directly (avoiding podman-compose bug)
- Refactored CLI to call kp3-service HTTP API instead of loading vLLM directly
- Added `--agent-name` / `-A` option with case-insensitive Letta API lookup

### Files Modified
- `kp3/src/kp3/config.py` - Changed to Qwen3-Embedding-0.6B model (~1.5GB VRAM)
- `v2-runtime/docker-compose.yml` - GPU passthrough and CUDA_VISIBLE_DEVICES=1
- `v2-runtime/kx` - Fixed cmd_kp3 to use podman directly
- `kp3/src/kp3/cli.py` - Major rewrite of passage_search, added agent name resolution

### Challenges & Solutions
- **Challenge**: vLLM `runner` parameter not supported in v0.8.x
  - **Solution**: Changed `runner="pooling"` to `task="embed"`

- **Challenge**: CUDA OOM on RTX 3050 (6GB) with 4B embedding model
  - **Solution**: Switched to Qwen3-Embedding-0.6B (~1.5GB VRAM)

- **Challenge**: GPU 0 memory exhausted by orphaned vLLM process
  - **Solution**: Found and killed orphaned process (PID 1190470) using 11.5GB

- **Challenge**: podman-compose run bug with `remove_orphans` attribute
  - **Solution**: Changed kx to use podman directly instead of podman-compose

- **Challenge**: CLI trying to load vLLM without GPU access in container
  - **Solution**: Refactored CLI to call kp3-service HTTP API

- **Challenge**: Letta API returning 307 redirect
  - **Solution**: Added trailing slash and `follow_redirects=True`

### Insights & Aha Moments
- The 0.6B embedding model provides good quality while leaving room for the main inference model
- Running CLI tools that need GPU models should call the service API, not load models directly
- Podman-compose has bugs with `run --rm` that require workarounds

### Next Steps
- [ ] Consider adding `--agent-name` support to other CLI commands
- [ ] Monitor GPU memory usage in production

### Commands Reference
```bash
# Search by agent name (case-insensitive)
kx kp3 passage search "query" --agent-name Corindel

# Search by agent ID
kx kp3 passage search "query" --agent agent-56a10649-420a-4639-83f3-575e12964442

# Check GPU usage
nvidia-smi
```
