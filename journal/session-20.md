---

## Session 20 - [Date: 2025-12-05]

### Goals
- [x] Debug Deepgram TTS 400 error
- [x] Set up proper Python logging (console + file)
- [x] Clear stale Redis jobs causing 404 errors
- [x] Test voice pipeline stability over extended use

### What We Covered
- Deepgram TTS API voice parameter format
- Python logging with multiple handlers
- SAQ/Redis job queue management
- Extended system stability testing

### Key Concepts Learned
1. **Deepgram TTS Voice Parameter**: The voice parameter should be just the voice name (`aura-2-phoebe-en`), not `model=aura-2-phoebe-en`. Pipecat didn't propagate the actual error from Deepgram, making this tricky to debug.

2. **Python Multi-Handler Logging**: Created a shared `logging_config.py` that configures both console and file handlers. Key pattern:
   ```python
   root_logger = logging.getLogger()
   root_logger.addHandler(console_handler)
   root_logger.addHandler(file_handler)
   ```

3. **Stale Redis Jobs**: When code changes but old jobs are still in the Redis queue, they execute with stale parameters baked in. Solution: `docker exec redis redis-cli FLUSHDB` to clear the queue.

4. **Python Bytecode Caching**: Set `PYTHONDONTWRITEBYTECODE=1` to prevent `.pyc` files from caching old code during development.

### What We Built
- `src/kairix_agent/logging_config.py` - Shared logging configuration
- Updated `server/main.py` and `worker/settings.py` to use shared logging
- Logs now written to `logs/server.log` and `logs/worker.log`

### Insights & Aha Moments
- **API error propagation matters**: Pipecat's TTS service gave a generic 400 error without the actual Deepgram error message. Had to reason about what could cause a 400 (invalid parameters) and check the voice format.
- **Redis queue persistence**: Jobs enqueued before code changes still run with old parameters. Important to flush Redis when making breaking changes to job signatures.

### Challenges & Solutions
- **Challenge**: Deepgram TTS returning 400 errors
- **Solution**: Fixed voice parameter format from `model=aura-2-phoebe-en` to `aura-2-phoebe-en`

- **Challenge**: Worker kept hitting 404s for a deleted message ID
- **Solution**: The source code was correct (passing `None`), but stale jobs in Redis had the old cursor baked in. Flushed Redis to clear them.

- **Challenge**: Wanted logs in files without using shell `tee`
- **Solution**: Created Python logging config with both StreamHandler (console) and FileHandler (file)

### Next Steps
- [ ] Add text sanitizer to strip markdown formatting before TTS
- [ ] Investigate MinWordsInterruptionStrategy for preventing accidental interrupts
- [ ] Consider VAD tuning per input source (different mics/environments)

### Questions/Blockers
- Smart Turn Detection (`LocalSmartTurnAnalyzerV3`) may not be compatible with `FastAPIWebsocketTransport` - needs investigation

### System Stability Report
After several hours of iOS app usage:
- Voice pipeline: Stable, no errors
- Background worker: Both cron jobs running every minute without failures
- Deepgram TTS: Working correctly with hosted service
- Letta integration: Streaming responses functioning properly
- Over 22,000 log lines generated with zero errors
