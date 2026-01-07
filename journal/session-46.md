## Session 46 - 2026-01-07

### Goals
- [x] Implement echo/feedback cancellation for voice pipeline
- [x] Fix iOS hardware AEC with AVAudioEngine

### What We Covered
- Designed and implemented layered echo cancellation approach
- Server-side adaptive VAD thresholds
- iOS client-side hardware AEC via AVAudioEngine voice processing

### Key Concepts Learned
1. **AVAudioEngine Voice Processing Quirks**: Enabling `setVoiceProcessingEnabled` causes the engine to stop itself due to configuration changes. Must observe `AVAudioEngineConfigurationChangeNotification` and restart.

2. **Proper Voice Processing Setup Sequence**:
   - Connect nodes BEFORE enabling voice processing
   - Enable on BOTH input AND output nodes
   - Get hardware format AFTER enabling (format may change)
   - Handle config change notifications

3. **Layered Echo Cancellation**: Two layers working together:
   - Layer 1 (Client): iOS hardware AEC via `setVoiceProcessingEnabled`
   - Layer 2 (Server): Adaptive VAD thresholds during bot speech

### What We Built

**Server-side (deployed to salinas):**
- `v2-runtime/src/kairix_agent/server/pipecat/echo_cancellation.py` - EchoCancellationProcessor that dynamically adjusts VAD `min_volume` during bot speech
- `PUT /agents/{agent_id}/echo-settings` - API endpoint for runtime threshold tuning

**Client-side (iOS):**
- Fixed `AudioStream.ios.kt` with proper voice processing setup:
  - Enable voice processing on both input and output nodes
  - Handle `AVAudioEngineConfigurationChangeNotification`
  - Restart engine after config changes

### Insights & Aha Moments
- `AVAudioSessionModeVoiceChat` alone does NOT enable AEC for AVAudioEngine - you must explicitly call `setVoiceProcessingEnabled(true)` on the I/O nodes
- The engine stops itself after enabling voice processing; this is expected behavior, not an error
- Voice processing must be enabled AFTER nodes are connected but BEFORE engine starts

### Challenges & Solutions
- **Challenge**: iOS client stopped receiving audio after enabling voice processing
- **Solution**: The engine was stopping due to config changes. Added notification observer to detect and restart engine.

- **Challenge**: Voice processing silently failing
- **Solution**: Enable on BOTH input AND output nodes, not just input

### Next Steps
- [ ] Test echo cancellation in various acoustic environments
- [ ] Tune adaptive VAD thresholds based on real-world usage
- [ ] Consider persisting echo settings per agent in database

### References
- [AVAudioEngine Tips Blog](https://snakamura.github.io/log/2024/11/audio_engine.html)
- [WWDC19 - What's New in AVAudioEngine](https://developer.apple.com/videos/play/wwdc2019/510/)
- [OpenAI Realtime Audio Notes](https://community.openai.com/t/audio-notes-for-openai-realtime-on-apple-platforms/1108404)
