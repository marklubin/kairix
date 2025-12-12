# Session 12 - Date: 2025-11-30

## Goals
- [x] Continue Pipecat voice pipeline integration
- [x] Fix interim transcription issue (partials going to LLM)
- [x] Fix audio playback speed (sample rate mismatch)
- [x] Tune VAD settings for less aggressive turn detection
- [ ] Address audio feedback loop (deferred)
- [ ] Get clean end-to-end voice conversation working

## What We Covered
- **Interim vs Final Transcriptions**: Deepgram sends both, must filter
- **Sample Rate Mismatch**: Piper outputs 22050Hz, client was playing at 16000Hz
- **Two-Layer VAD**: Both Pipecat VAD and Deepgram have silence detection
- **Turn Detection Tuning**: Adjusting `stop_secs` and `utterance_end_ms`

## Key Concepts Learned

1. **InterimTranscriptionFrame Inheritance Gotcha**
   - `InterimTranscriptionFrame` is a subclass of `TranscriptionFrame`
   - `isinstance(frame, TranscriptionFrame)` matches BOTH
   - Must check for more specific subclass first
   - Classic OOP inheritance pitfall in type checking

2. **Sample Rate = Pitch + Speed**
   - Playing 22050Hz audio at 16000Hz = ~30% slower and lower pitched
   - Ratio: 16000/22050 ≈ 0.73
   - Voice pipelines often have asymmetric rates (STT vs TTS)
   - Deepgram prefers 16kHz input, Piper outputs 22050Hz

3. **Two-Layer Silence Detection**
   | Layer | Setting | Controls |
   |-------|---------|----------|
   | Deepgram STT | `utterance_end_ms` | When transcript finalizes |
   | Pipecat VAD | `stop_secs` | When "user stopped speaking" fires |
   - Both can cut you off - must tune both
   - They serve different purposes but overlap in effect

4. **VADParams Configuration**
   ```python
   VADParams(
       stop_secs=1.5,    # Silence before "done speaking"
       start_secs=0.2,   # Speech before "started speaking"
       min_volume=0.6,   # Volume threshold
   )
   ```

5. **Deepgram LiveOptions**
   ```python
   LiveOptions(
       utterance_end_ms="2000",  # String, not int (SDK type annotation wrong)
       interim_results=True,      # Get partial transcripts
       vad_events=True,           # Voice activity events
   )
   ```

## What We Built

**letta_llm.py** - Fixed interim transcription filtering:
```python
def _extract_message(self, frame: Frame) -> str | None:
    # Check subclass FIRST due to inheritance
    if isinstance(frame, InterimTranscriptionFrame):
        return None
    if isinstance(frame, TranscriptionFrame):
        return frame.text
    ...
```

**voice_client.py** - Fixed asymmetric sample rates:
```python
SAMPLE_RATE_IN = 16000   # For Deepgram STT
SAMPLE_RATE_OUT = 22050  # For Piper TTS (ljspeech-high model)
```

**main.py** - VAD and Deepgram tuning:
```python
vad = SileroVADAnalyzer(
    params=VADParams(stop_secs=1.5)
)

stt = DeepgramSTTService(
    api_key=deepgram_api_key,
    live_options=LiveOptions(
        utterance_end_ms="2000",
        ...
    ),
)
```

## Insights & Aha Moments

- **"Check subclass first"**: OOP inheritance means parent matches child - order matters in isinstance chains
- **"Asymmetric rates are normal"**: STT optimized for different sample rate than TTS
- **"Two things can cut you off"**: VAD and STT both have silence detection, tune both
- **"SDK type hints lie"**: `utterance_end_ms` typed as `str | None` but documented as milliseconds

## Challenges & Solutions

- **Challenge**: Letta receiving fragmented messages like "Ack message", "received."
- **Solution**: Added explicit check for `InterimTranscriptionFrame` before `TranscriptionFrame`

- **Challenge**: Audio playing at half speed, sounding slow and low-pitched
- **Solution**: Changed playback rate from 16000Hz to 22050Hz to match Piper model

- **Challenge**: Turn detection still too aggressive even after VAD tuning
- **Solution**: Added `utterance_end_ms=2000` to Deepgram config (ongoing - still needs work)

## Next Steps (Debugging VAD)

**Still fragmented - investigate:**
1. Check if `min_volume` threshold is too sensitive
2. Look for max utterance length settings in Deepgram
3. Consider disabling Pipecat VAD entirely, rely only on Deepgram
4. Add logging to see exact timing of "User stopped speaking" events
5. Test with `endpointing` parameter in Deepgram (different from `utterance_end_ms`)

**Other deferred items:**
- [ ] Audio feedback loop (mute mic during playback)
- [ ] Test on Android
- [ ] Connect KMP mobile app to this backend

## Questions/Blockers
- VAD still cutting off mid-sentence despite tuning
- Need to understand interaction between Pipecat VAD and Deepgram endpointing
- May need to look at Pipecat source to understand frame flow

## Technical Notes

**Current Pipeline:**
```
Mic (16kHz) → WebSocket → Deepgram STT → LettaLLMService → Piper TTS (22050Hz) → Speaker
```

**Files Modified This Session:**
- `src/agent_server/pipecat/letta_llm.py` - InterimTranscriptionFrame filtering
- `src/agent_server/voice_client.py` - Asymmetric sample rates
- `src/agent_server/main.py` - VAD params, Deepgram LiveOptions
- `docker-compose.yml` - Voice model change (ljspeech-high)

## Session Victory

**Fixed two major bugs:**
1. Partial transcripts no longer sent to LLM
2. Audio plays at correct speed

Voice pipeline is functional but turn detection needs more tuning. Good stopping point!
