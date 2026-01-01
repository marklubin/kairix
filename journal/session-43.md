## Session 43 - 2025-12-31

### Goals
- [x] Verify step_memory NO_UPDATE_NEEDED detection fix works
- [x] Extract shared utility function for detection logic
- [x] Deploy and test on salinas
- [x] Restore corrupted Corindel blocks from KP3 refs

### What We Covered
- Critical bug fix: NO_UPDATE_NEEDED detection was broken in `block_manager.py`
- Refactored detection logic into shared utility module
- Block restoration from KP3 refs system
- Deployment troubleshooting (cache invalidation)

### Key Concepts Learned
1. **Dual update paths**: The step_memory.py `_parse_step_response()` only parsed for logging - the actual block update happens in `block_manager.py` which had the old broken logic
2. **Cache invalidation on deploy**: `git pull` cache can miss changes if images are cached; use `--no-cache` or `git reset --hard origin/main` to force fresh builds
3. **KP3 refs system works**: Successfully used refs to restore corrupted blocks from passage history

### What We Built
- `src/kairix_agent/llm/utils.py` - New shared utility module with `should_skip_block_update()` function
- Updated `src/kairix_agent/llm/block_manager.py` to use shared function
- Updated `src/kairix_agent/worker/jobs/step_memory.py` to use shared function
- Updated `src/kairix_agent/llm/__init__.py` to export the shared function

### Insights & Aha Moments
- The bug caused blocks to be overwritten with LLM rationale text when responses contained "NO_UPDATE_NEEDED" anywhere but not at the start (e.g., `**NO_UPDATE_NEEDED:**` markdown format)
- Having the logic in two places (`block_manager.py` for actual update, `step_memory.py` for logging) was a maintenance hazard - extracting to shared function prevents future drift

### Challenges & Solutions
- **Challenge**: Fix in step_memory.py didn't work because actual update happens in block_manager.py
- **Solution**: Found the real update logic in block_manager.py line 129 and fixed there too

- **Challenge**: Deploy cache hit old code even after git push
- **Solution**: Used `git reset --hard origin/main && ./kx build --no-cache`

- **Challenge**: KP3 API returns 404 for passages without agent_id header (after agent_id segmentation)
- **Solution**: Used psql directly to extract passage content from database

### Code Changes

**New file: `llm/utils.py`**
```python
def should_skip_block_update(response: str) -> bool:
    """Check if NO_UPDATE_NEEDED appears anywhere in response."""
    return "NO_UPDATE_NEEDED" in response.upper()
```

**Updated: `block_manager.py`**
```python
# Before (broken):
if result.upper().startswith("NO_UPDATE_NEEDED"):

# After (fixed):
if should_skip_block_update(result):
```

### Next Steps
- [ ] Add `kx kp3 refs rollback` command for easier block restoration
- [ ] Backfill agent_id on existing KP3 passages for Corindel

### Commits
- `86a5a70` - fix: Check for NO_UPDATE_NEEDED anywhere in response in block_manager.py
- `5cc66e3` - refactor: Extract should_skip_block_update to shared utils module
